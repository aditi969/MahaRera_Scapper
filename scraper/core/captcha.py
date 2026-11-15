"""OpenCV + Tesseract automated CAPTCHA solver for MahaRERA.

Matches exact image preprocessing (CLAHE, Otsu, adaptive thresholding)
and submission/retry logic from Cell 4 of RERA_Scrapping_fixed_v3.ipynb.
"""
import base64
import os
import re
import shutil
import time
from typing import Optional

try:
    import cv2
except ImportError:
    cv2 = None

from PIL import Image
import pytesseract
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


class CaptchaSolver:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger):
        self.config = config
        self.logger = logger
        candidate_paths = [
            self.config.tesseract_path,
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            shutil.which("tesseract") or "",
        ]
        for path in candidate_paths:
            if path and os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

    @staticmethod
    def clean_captcha(captcha_text: str) -> str:
        captcha_text = (captcha_text or "").upper()
        return re.sub(r"[^A-Z0-9]", "", captcha_text)

    def process_captcha_with_opencv(self, image_path: str) -> str:
        if cv2 is None:
            # Fallback when OpenCV is not installed: use PIL
            try:
                img = Image.open(image_path).convert('L')
                config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                text = pytesseract.image_to_string(img, config=config).strip()
                return self.clean_captcha(text)
            except Exception:
                return ""

        img = cv2.imread(image_path)
        if img is None:
            return ""

        img_padded = cv2.copyMakeBorder(img, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=[255, 255, 255])
        gray = cv2.cvtColor(img_padded, cv2.COLOR_BGR2GRAY)

        config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        resized = cv2.resize(gray, None, fx=3.5, fy=3.5, interpolation=cv2.INTER_CUBIC)

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(resized)
        try:
            text1 = pytesseract.image_to_string(enhanced, config=config).strip()
            c1 = self.clean_captcha(text1)
            if len(c1) == 6:
                return c1
        except Exception:
            c1 = ""

        try:
            _, thresh_otsu = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text2 = pytesseract.image_to_string(thresh_otsu, config=config).strip()
            c2 = self.clean_captcha(text2)
            if len(c2) == 6:
                return c2
        except Exception:
            c2 = ""

        try:
            adaptive_thresh = cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            text3 = pytesseract.image_to_string(adaptive_thresh, config=config).strip()
            c3 = self.clean_captcha(text3)
            if len(c3) == 6:
                return c3
        except Exception:
            c3 = ""

        try:
            text4 = pytesseract.image_to_string(resized, config=config).strip()
            c4 = self.clean_captcha(text4)
            if len(c4) == 6:
                return c4
        except Exception:
            c4 = ""

        candidates = [c for c in [c1, c2, c3, c4] if c]
        if candidates:
            candidates.sort(key=lambda x: (abs(len(x) - 6), -len(x)))
            return candidates[0]
        return ""

    def _get_captcha_data_url(self, driver, elem) -> Optional[str]:
        return driver.execute_script('''
            var elem = arguments[0];
            if (!elem) return null;
            var tag = elem.tagName.toLowerCase();

            if (tag === 'img') {
                if (elem.src && elem.src.indexOf('data:image') === 0) {
                    return elem.src;
                }
            }

            if (tag === 'canvas') {
                try { return elem.toDataURL('image/png'); } catch (e) { return null; }
            }

            var canvas = document.createElement('canvas');
            canvas.width = elem.naturalWidth || elem.width || elem.clientWidth || 300;
            canvas.height = elem.naturalHeight || elem.height || elem.clientHeight || 80;
            var ctx = canvas.getContext('2d');
            ctx.drawImage(elem, 0, 0, canvas.width, canvas.height);
            try { return canvas.toDataURL('image/png'); } catch (e) { return null; }
        ''', elem)

    def wait_for_captcha_ready(self, driver, captcha_element, timeout: int = 6):
        try:
            WebDriverWait(driver, timeout).until(lambda d: d.execute_script('''
                var el = arguments[0];
                if (!el) return false;
                if (el.tagName.toLowerCase() === 'img') {
                    return el.complete && el.naturalWidth > 0;
                }
                return true;
            ''', captcha_element))
        except TimeoutException:
            pass

    def save_captcha_image_from_canvas(self, driver, captcha_element, save_path: str = "captcha_image.png") -> str:
        try:
            self.wait_for_captcha_ready(driver, captcha_element)
            data_url = self._get_captcha_data_url(driver, captcha_element)
            if data_url:
                base64_data = data_url.split(',')[1]
                img_bytes = base64.b64decode(base64_data)
                with open(save_path, "wb") as f:
                    f.write(img_bytes)
                return save_path
        except Exception:
            pass

        captcha_element.screenshot(save_path)
        return save_path

    def solve_one_captcha(self, driver, image_name: str = "captcha_image.png") -> str:
        try:
            captcha_image_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "captcahCanvas"))
            )
            self.save_captcha_image_from_canvas(driver, captcha_image_element, image_name)
        except StaleElementReferenceException:
            time.sleep(1)
            captcha_image_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "captcahCanvas"))
            )
            self.save_captcha_image_from_canvas(driver, captcha_image_element, image_name)

        raw_text = self.process_captcha_with_opencv(image_name)
        return self.clean_captcha(raw_text)

    def submit_captcha(self, driver, captcha_text: str):
        captcha_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
        )
        captcha_input.clear()
        captcha_input.send_keys(captcha_text)
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@class='btn btn-primary next']"))
        )
        driver.execute_script("arguments[0].click();", submit_button)
        time.sleep(2)

    def captcha_was_rejected(self, driver) -> bool:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//p[@id='letter'][contains(text(), 'Invalid Captcha')]"))
            )
            return True
        except TimeoutException:
            return False

    def dismiss_invalid_captcha_popup(self, driver):
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn-primary-messagebox')]"))
            ).click()
            time.sleep(1.5)
        except Exception:
            pass

    def solve_captcha_fully_automated(self, driver, image_name: str = "captcha_image.png") -> bool:
        for refresh_round in range(self.config.refresh_attempts + 1):
            for ocr_attempt in range(1, self.config.max_captcha_ocr_attempts + 1):
                try:
                    captcha_text = self.solve_one_captcha(driver, image_name)
                    self.logger.info(f"🔎 Captcha OCR attempt {ocr_attempt} -> '{captcha_text}'")
                    self.submit_captcha(driver, captcha_text)

                    if self.captcha_was_rejected(driver):
                        self.logger.info("❌ Invalid captcha, retrying automatically...")
                        self.dismiss_invalid_captcha_popup(driver)
                        continue
                    else:
                        self.logger.info("✅ Captcha accepted.")
                        return True
                except Exception as e:
                    self.logger.warning(f"Captcha attempt error: {e}")
                    time.sleep(1.5)

            if refresh_round < self.config.refresh_attempts:
                self.logger.info(f"🔄 Refreshing captcha (refresh round {refresh_round + 1}/{self.config.refresh_attempts})...")
                try:
                    driver.refresh()
                    time.sleep(self.config.page_load_wait)
                except Exception:
                    pass

        self.logger.error("🚫 CAPTCHA_BLOCKED: CAPTCHA could not be resolved automatically within bounded limit. Recording failure and continuing.")
        return False
