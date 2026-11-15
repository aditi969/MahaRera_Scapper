"""Certificate date extraction from PDF text layer and OCR fallback.

Matches exact logic and date normalization from Cell 4 of RERA_Scrapping_fixed_v3.ipynb.
"""
import base64
import io
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pytesseract
from PIL import Image
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger

_FIND_CERT_ICON_JS = """
    var all = document.querySelectorAll('*');
    var label = null;
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var txt = (el.innerText || el.textContent || '').trim();
        if (txt === 'Certificate Download' || txt.indexOf('Certificate Download') === 0) {
            var hasChild = false;
            for (var j = 0; j < el.children.length; j++) {
                var ctxt = (el.children[j].innerText || el.children[j].textContent || '').trim();
                if (ctxt.indexOf('Certificate Download') === 0) { hasChild = true; break; }
            }
            if (!hasChild) { label = el; break; }
        }
    }

    if (label) {
        var container = label.closest('div.d-flex, div.col-12, div') || label.parentElement;
        if (container) {
            var btn = container.querySelector('a, button, i.bi-cloud-download, [title*="Certificate" i]');
            if (btn) return btn.closest('a, button') || btn;
        }
        var sib = label.nextElementSibling;
        while (sib) {
            if (sib.matches('a, button, i') || sib.querySelector('a, button, i')) {
                var el = sib.querySelector('a, button, i') || sib;
                return el.closest('a, button') || el;
            }
            sib = sib.nextElementSibling;
        }
    }

    var icon = document.querySelector('a[title*="Certificate" i], button[title*="Certificate" i], i.bi-cloud-download, [data-toggle="tooltip"][title*="Certificate" i]');
    if (icon) return icon.closest('a, button') || icon;

    return null;
"""

_BLOB_TO_B64_JS = """
    var blobUrl = arguments[0];
    var done    = arguments[1];
    fetch(blobUrl)
        .then(function(r){ return r.blob(); })
        .then(function(blob){\n            var reader = new FileReader();
            reader.onloadend = function(){ done(reader.result); };
            reader.onerror   = function(){ done(null); };
            reader.readAsDataURL(blob);
        })
        .catch(function(){ done(null); });
"""

_CERT_MIN_YEAR, _CERT_MAX_YEAR = 2010, 2045
_OCR_DIGIT_FIX = str.maketrans({
    'O': '0', 'o': '0', 'Q': '0', 'D': '0',
    'l': '1', 'I': '1', 'i': '1', '|': '1',
    'S': '5', 's': '5', 'B': '8', 'Z': '2'
})


class CertificateExtractor:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger):
        self.config = config
        self.logger = logger
        if os.path.exists(self.config.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_path

    def close_modal(self, driver, modal_locator=(By.CSS_SELECTOR, "div.modal.show"), timeout: int = 4):
        try:
            modal = WebDriverWait(driver, 2).until(EC.visibility_of_element_located(modal_locator))
        except TimeoutException:
            return

        try:
            close_btn = modal.find_element(By.CSS_SELECTOR, "button.btn-close, [data-bs-dismiss='modal']")
            driver.execute_script("arguments[0].click();", close_btn)
            WebDriverWait(driver, timeout).until(EC.invisibility_of_element_located(modal_locator))
            return
        except Exception:
            pass

        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        except Exception:
            pass

        try:
            driver.execute_script("""
                document.querySelectorAll('div.modal.show').forEach(function(m){
                    m.classList.remove('show'); m.style.display = 'none';
                });
                document.querySelectorAll('.modal-backdrop').forEach(function(b){ b.remove(); });
                document.body.classList.remove('modal-open');
            """)
        except Exception:
            pass

    def find_certificate_download_icon(self, driver, wait_s: float = 6.0):
        """Locate specifically the Certificate Download icon/button in the Project Details header card."""
        end = time.time() + wait_s
        while True:
            try:
                el = driver.execute_script(_FIND_CERT_ICON_JS)
                if el is not None:
                    return el
            except Exception:
                pass
            if time.time() >= end:
                break
            time.sleep(0.3)
        return None

    def find_cert_button(self, driver):
        """Find the Certificate Download button using JS inspection followed by robust specific XPaths."""
        btn = None
        try:
            btn = self.find_certificate_download_icon(driver, wait_s=6.0)
        except Exception as _e:
            self.logger.warning(f"[CERT] Icon search error: {_e}")

        if btn is None:
            _xpaths = [
                "//i[contains(@class, 'bi-cloud-download')]/ancestor-or-self::a",
                "//i[contains(@class, 'bi-cloud-download')]/ancestor-or-self::button",
                "//a[.//i[contains(@class, 'bi-cloud-download')]]",
                "//button[.//i[contains(@class, 'bi-cloud-download')]]",
                "//*[contains(text(), 'Certificate Download')]/following::a[1]",
                "//*[contains(text(), 'Certificate Download')]/following::button[1]",
                "//*[contains(text(), 'Certificate Download')]/ancestor::div[contains(@class, 'd-flex')]//a",
                "//*[contains(text(), 'Certificate Download')]/ancestor::div[contains(@class, 'd-flex')]//button",
                "//a[contains(@href, 'certificate') or contains(@href, 'Certificate')]",
                "//a[contains(@title, 'Certificate') or contains(@title, 'certificate')]",
                "//button[contains(@title, 'Certificate') or contains(@title, 'certificate')]",
                "//i[contains(@class, 'bi-cloud-download')]",
                "//*[@title='Download Certificate']",
                "//*[@data-original-title='Download Certificate']"
            ]
            for xp in _xpaths:
                try:
                    els = driver.find_elements(By.XPATH, xp)
                    for el in els:
                        if el.is_displayed():
                            return el
                except Exception:
                    pass
        return btn

    @staticmethod
    def cert_norm_date(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        s = str(s).strip()
        s = s.translate(_OCR_DIGIT_FIX)
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d'):
            try:
                dt = datetime.strptime(s, fmt)
                if _CERT_MIN_YEAR <= dt.year <= _CERT_MAX_YEAR:
                    return dt.strftime('%d-%m-%Y')
            except ValueError:
                pass
        return None

    @staticmethod
    def cert_to_dt(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.strptime(s, '%d-%m-%Y')
        except Exception:
            return None

    def extract_cert_fields_from_text(self, raw_text: str) -> Dict[str, Optional[str]]:
        if not raw_text:
            return {'Commencing From': None, 'Leftmost Date': None, 'Ending With': None}

        clean = re.sub(r'[\s\xa0\u200b]+', ' ', raw_text)

        m_c = re.search(r'commencing\s+from\s+([0-9OoIlSsBZ\-/.]+)', clean, re.I)
        m_e = re.search(r'ending\s+with\s+([0-9OoIlSsBZ\-/.]+)', clean, re.I)
        m_l = re.search(r'[Dd]ated\s*:\s*([0-9OoIlSsBZ\-/.]+)', clean, re.I)

        c = self.cert_norm_date(m_c.group(1)) if m_c else None
        e = self.cert_norm_date(m_e.group(1)) if m_e else None
        l = self.cert_norm_date(m_l.group(1)) if m_l else None

        if not (c and e and l):
            compact = re.sub(r'\s+', '', clean)
            _C = r'[0-9OoQDlIi|SsBZ]'
            _D = r'(' + _C + r'{1,2}[\-/.,]' + _C + r'{1,2}[\-/.,]' + _C + r'{4})'
            _SEP = r'[:;\s,\-/.]*'
            if not c:
                mc2 = re.search(r'commenc[A-Za-z]{0,8}' + _SEP + r'fr[A-Za-z]{0,5}' + _SEP + _D, compact, re.I)
                if mc2:
                    c = self.cert_norm_date(mc2.group(1))
            if not e:
                me2 = re.search(r'ending' + _SEP + r'w[A-Za-z]{0,6}' + _SEP + _D, compact, re.I)
                if me2:
                    e = self.cert_norm_date(me2.group(1))
            if not l:
                ml2 = re.findall(r'[Dd]ated' + _SEP + _D, compact, re.I)
                if ml2:
                    l = self.cert_norm_date(ml2[-1])

        return {'Commencing From': c, 'Leftmost Date': l, 'Ending With': e}

    def parse_certificate_pdf(self, pdf_bytes: bytes, tag: str = '') -> Tuple[Dict[str, Optional[str]], Dict[str, str]]:
        """Parse certificate PDF: 1) Try text layer first; 2) Fall back to OCR on rendered pages if needed."""
        try:
            import pymupdf as fitz
        except ImportError:
            try:
                import fitz
            except ImportError:
                fitz = None

        best = {'Commencing From': None, 'Leftmost Date': None, 'Ending With': None}
        sources = {'Commencing From': 'NOT_READ', 'Leftmost Date': 'NOT_READ', 'Ending With': 'NOT_READ'}

        if not fitz or not pdf_bytes:
            return best, sources

        doc = None
        try:
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        except Exception as e:
            self.logger.warning(f"[CERT] Failed to open PDF bytes: {e}")
            return best, sources

        try:
            # --- Step 1: PDF Text Layer ---
            full_text = '\n'.join(page.get_text() for page in doc)
            if full_text.strip():
                text_fields = self.extract_cert_fields_from_text(full_text)
                for k in ('Commencing From', 'Leftmost Date', 'Ending With'):
                    if text_fields[k]:
                        best[k] = text_fields[k]
                        sources[k] = 'PDF_TEXT'

            # --- Step 2: OCR Fallback if any date is missing ---
            if not all(best.values()):
                self.logger.info(f"[CERT] {tag} Text layer incomplete ({best}) — running OCR on rendered pages...")
                ocr_dump = []
                for pg in doc:
                    try:
                        pix = pg.get_pixmap(dpi=300)
                        img = Image.open(io.BytesIO(pix.tobytes('png')))
                        ocr_text = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6', timeout=60)
                        ocr_dump.append(ocr_text)
                        ocr_fields = self.extract_cert_fields_from_text(ocr_text)
                        for k in ('Commencing From', 'Leftmost Date', 'Ending With'):
                            if not best[k] and ocr_fields[k]:
                                best[k] = ocr_fields[k]
                                sources[k] = 'OCR'
                        if all(best.values()):
                            break
                    except Exception as ocr_err:
                        self.logger.warning(f"[CERT] OCR error on page: {ocr_err}")

            self.logger.info(f"[CERT] {tag} Extracted PDF dates -> {best} | sources={sources}")
            return best, sources
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass

    def finalize_cert_dates(self, cert: Dict[str, Optional[str]], cert_sources: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
        out = {
            'Commencing From': cert.get('Commencing From'),
            'Leftmost Date': cert.get('Leftmost Date'),
            'Ending With': cert.get('Ending With'),
        }
        src = cert_sources or {}
        parts = []
        for k in ('Commencing From', 'Leftmost Date', 'Ending With'):
            val = out[k]
            method = src.get(k, 'PDF_TEXT' if val else 'NOT_READ')
            parts.append(f"{k}={method}")

        c_dt = self.cert_to_dt(out['Commencing From'])
        e_dt = self.cert_to_dt(out['Ending With'])
        if c_dt and e_dt and c_dt > e_dt:
            parts.append('CHECK:commencing_after_ending')

        out['Cert_Date_Source'] = '; '.join(parts)
        return out

    def extract_certificate_dates(self, driver, button) -> Dict[str, Any]:
        """Download and extract certificate dates with multi-attempt retry and full blob handling."""
        empty = {'Commencing From': None, 'Leftmost Date': None, 'Ending With': None, '_sources': {}, 'status': 'DOWNLOAD_FAILED'}
        try:
            proj_tag = re.sub(r'\W+', '_', driver.current_url.rstrip('/').split('/')[-1])
        except Exception:
            proj_tag = ''

        max_attempts = max(self.config.cert_max_retries, 2)
        load_timeout = max(self.config.cert_load_timeout, 10)

        for attempt in range(1, max_attempts + 1):
            orig_handles = set(driver.window_handles)
            main_handle = driver.current_window_handle
            new_tab = None

            try:
                _target = button
                if attempt > 1:
                    _alt = self.find_cert_button(driver)
                    if _alt is not None:
                        _target = _alt

                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", _target)
                time.sleep(0.3)

                clickable = driver.execute_script("var el = arguments[0]; return el.closest('a, button') || el;", _target)

                # Click download button with multiple fallbacks
                if attempt == 1:
                    try:
                        clickable.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", clickable)
                elif attempt == 2:
                    driver.execute_script("arguments[0].click();", clickable)
                else:
                    ActionChains(driver).move_to_element(clickable).pause(0.3).click().perform()

                # Bounded wait for new tab
                try:
                    WebDriverWait(driver, load_timeout).until(
                        lambda d: set(d.window_handles) - orig_handles
                    )
                except TimeoutException:
                    self.logger.info(f"[CERT] No new tab within {load_timeout}s (attempt {attempt}/{max_attempts})")
                    continue

                new_tab = list(set(driver.window_handles) - orig_handles)[0]
                driver.switch_to.window(new_tab)

                try:
                    WebDriverWait(driver, load_timeout).until(
                        lambda d: d.current_url.startswith('blob:')
                    )
                except TimeoutException:
                    self.logger.info(f"[CERT] New tab did not resolve to blob URL (attempt {attempt})")
                    driver.close()
                    driver.switch_to.window(main_handle)
                    new_tab = None
                    continue

                pdf_data = driver.execute_async_script(_BLOB_TO_B64_JS, driver.current_url)
                driver.close()
                driver.switch_to.window(main_handle)
                new_tab = None

                if not pdf_data or not pdf_data.startswith('data:'):
                    self.logger.info(f"[CERT] Blob returned empty data (attempt {attempt})")
                    time.sleep(1)
                    continue

                pdf_bytes = base64.b64decode(pdf_data.split(',', 1)[1])
                best, sources = self.parse_certificate_pdf(pdf_bytes, proj_tag)

                status = "SUCCESS" if any(best.values()) else "NO_DATES_FOUND"
                return {
                    'Commencing From': best['Commencing From'],
                    'Leftmost Date': best['Leftmost Date'],
                    'Ending With': best['Ending With'],
                    '_sources': sources,
                    'status': status
                }

            except Exception as e:
                self.logger.warning(f"[CERT] Extraction attempt {attempt} failed: {e}")
                if new_tab and new_tab in driver.window_handles:
                    try:
                        driver.switch_to.window(new_tab)
                        driver.close()
                    except Exception:
                        pass
                try:
                    driver.switch_to.window(main_handle)
                except Exception:
                    pass
                time.sleep(1)

        return empty

    def get_cert_dates_with_retries(self, driver, df: Optional[pd.DataFrame] = None) -> Dict[str, Optional[str]]:
        """Run certificate extraction with retries matching the original notebook workflow."""
        keys = ('Commencing From', 'Leftmost Date', 'Ending With')
        best = {k: None for k in keys}
        best_sources = {k: 'NOT_READ' for k in keys}
        full_passes = max(self.config.cert_full_retries, 2)

        for p in range(1, full_passes + 1):
            try:
                self.close_modal(driver)
            except Exception:
                pass
            try:
                # Certificate button is in the top header card: scroll to top
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
            except Exception:
                pass

            btn = self.find_cert_button(driver)
            if btn is None:
                self.logger.info(f"[CERT] Certificate button not found pass {p}/{full_passes}")
                time.sleep(1)
                continue

            res = self.extract_certificate_dates(driver, btn)
            res_sources = res.get('_sources', {})
            for k in keys:
                if not best[k] and res.get(k):
                    best[k] = res[k]
                    best_sources[k] = res_sources.get(k, 'PDF_TEXT')

            if all(best.values()):
                break

        # Validated fallbacks matching notebook Cell 6 so Commencing From / Leftmost Date / Ending With are never null
        if df is not None and not df.empty:
            reg_date = None
            rev_date = None
            orig_date = None
            last_mod = None

            if "Date of Registration" in df.columns and len(df["Date of Registration"]) > 0:
                v = df["Date of Registration"].iloc[0]
                if pd.notna(v) and str(v).strip():
                    reg_date = str(v).strip()

            if "Project proposed completion date revised" in df.columns and len(df["Project proposed completion date revised"]) > 0:
                v = df["Project proposed completion date revised"].iloc[0]
                if pd.notna(v) and str(v).strip():
                    rev_date = str(v).strip()

            if "Project proposed completion date original" in df.columns and len(df["Project proposed completion date original"]) > 0:
                v = df["Project proposed completion date original"].iloc[0]
                if pd.notna(v) and str(v).strip():
                    orig_date = str(v).strip()

            if "Last_Modified" in df.columns and len(df["Last_Modified"]) > 0:
                v = df["Last_Modified"].iloc[0]
                if pd.notna(v) and str(v).strip():
                    last_mod = str(v).strip()

            if not best.get("Commencing From"):
                norm_reg = self.cert_norm_date(reg_date) or reg_date
                if norm_reg:
                    best["Commencing From"] = norm_reg
                    best_sources["Commencing From"] = "FALLBACK:Date_of_Registration"

            if not best.get("Ending With"):
                norm_end = self.cert_norm_date(rev_date) or self.cert_norm_date(orig_date) or rev_date or orig_date
                if norm_end:
                    best["Ending With"] = norm_end
                    best_sources["Ending With"] = "FALLBACK:Proposed_Completion_Date"

            if not best.get("Leftmost Date"):
                norm_left = self.cert_norm_date(rev_date) or self.cert_norm_date(last_mod) or self.cert_norm_date(reg_date) or rev_date or reg_date
                if norm_left:
                    best["Leftmost Date"] = norm_left
                    best_sources["Leftmost Date"] = "FALLBACK:Endorsement_Date"

        final = self.finalize_cert_dates(best, cert_sources=best_sources)
        final['cert_extraction_status'] = 'SUCCESS' if any(best.values()) else ('NOT_AVAILABLE' if not any(best.values()) and best_sources.get('Commencing From') == 'NOT_READ' else 'NOT_EXTRACTED')
        self.logger.info(f"[CERT] FINAL DATES: {final}")
        return final
