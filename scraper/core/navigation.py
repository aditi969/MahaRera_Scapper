"""Search navigation, district filtering, and pagination for MahaRERA search.

Matches exact logic and selectors from Cell 3 of RERA_Scrapping_fixed_v3.ipynb.
"""
import math
import re
import time
import urllib.parse
from typing import Optional, Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from scraper.core.browser import BrowserManager
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger

# Official 36 Maharashtra Districts & Codes mapping
MAHARASHTRA_DISTRICT_CODE_MAP = {
    "ahmednagar": "522",
    "ahilyanagar": "522",
    "akola": "501",
    "amravati": "503",
    "aurangabad": "515",
    "chhatrapati sambhajinagar": "515",
    "beed": "523",
    "bhandara": "506",
    "buldhana": "500",
    "chandrapur": "509",
    "dhule": "498",
    "gadchiroli": "508",
    "gondia": "507",
    "hingoli": "512",
    "jalgaon": "499",
    "jalna": "514",
    "kolhapur": "530",
    "latur": "524",
    "mumbai": "519",
    "mumbai city": "519",
    "mumbai suburban": "518",
    "suburban": "518",
    "nagpur": "505",
    "nanded": "511",
    "nandurbar": "497",
    "nashik": "516",
    "nasik": "516",
    "osmanabad": "525",
    "dharashiv": "525",
    "palghar": "532",
    "parbhani": "513",
    "pune": "521",
    "raigarh": "520",
    "raigad": "520",
    "ratnagiri": "528",
    "sangli": "531",
    "satara": "527",
    "sindhudurg": "529",
    "solapur": "526",
    "thane": "517",
    "wardha": "504",
    "washim": "502",
    "yavatmal": "510",
}


def resolve_district_code(name: str) -> Optional[str]:
    """Resolve district name or partial string to official MahaRERA district code."""
    if not name:
        return None
    c_name = name.strip().lower()
    if c_name in MAHARASHTRA_DISTRICT_CODE_MAP:
        return MAHARASHTRA_DISTRICT_CODE_MAP[c_name]
    for k, v in MAHARASHTRA_DISTRICT_CODE_MAP.items():
        if k in c_name or c_name in k:
            return v
    return None


class NavigationManager:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger, browser: BrowserManager):
        self.config = config
        self.logger = logger
        self.browser = browser
        self.is_last_page_reached: bool = False
        self.canonical_page_url_template: Optional[str] = None

    def select_state_dropdown(self, driver, state_name: str = "Maharashtra", timeout: int = 8) -> bool:
        """Select state from the native <select> dropdown so district options load."""
        if not state_name:
            return True
        state_xpaths = [
            "//select[@id='edit-project-state']",
            "//select[contains(translate(@id,'STATE','state'),'state') or contains(translate(@name,'STATE','state'),'state')]"
        ]
        start_t = time.time()
        while time.time() - start_t < timeout:
            for sx in state_xpaths:
                try:
                    els = driver.find_elements(By.XPATH, sx)
                    if els:
                        sel = Select(els[0])
                        for opt in sel.options:
                            if state_name.lower() in opt.text.lower():
                                sel.select_by_visible_text(opt.text)
                                driver.execute_script("""
                                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                """, els[0])
                                self.logger.info(f"📍 State set to '{opt.text}'.")
                                time.sleep(1)
                                return True
                except Exception:
                    pass
            time.sleep(0.5)

        # Fallback: force set official Maharashtra code 27
        try:
            for sx in state_xpaths:
                els = driver.find_elements(By.XPATH, sx)
                if els:
                    driver.execute_script("""
                        var sel = arguments[0];
                        var opt = document.createElement('option');
                        opt.value = '27';
                        opt.text = 'MAHARASHTRA';
                        opt.selected = true;
                        sel.appendChild(opt);
                        sel.value = '27';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        sel.dispatchEvent(new Event('input', { bubbles: true }));
                    """, els[0])
                    self.logger.info("📍 State set to 'MAHARASHTRA' (code: 27, forced fallback).")
                    time.sleep(1)
                    return True
        except Exception as e:
            self.logger.warning(f"Could not select state '{state_name}': {e}")
        return False

    def select_district_dropdown(self, driver, district_name: str, max_retries: int = 3) -> bool:
        if not district_name:
            return True

        target_name = district_name.strip()
        skip_names = ("all", "all districts", "all / any district", "select district", "--select district--", "any", "multiple", "")
        if target_name.lower() in skip_names:
            self.logger.info("📍 Searching across all districts (no specific district filter applied).")
            return True

        district_code = resolve_district_code(target_name)
        if not district_code and getattr(self.config, "district_code", None):
            district_code = str(self.config.district_code).strip()

        xpath_native = (
            "//select[contains(translate(@formcontrolname,'DISTRICT','district'),'district') "
            "or contains(translate(@id,'DISTRICT','district'),'district') "
            "or contains(translate(@name,'DISTRICT','district'),'district')]"
        )

        for attempt in range(1, max_retries + 1):
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_native)))
                dropdown_el = driver.find_element(By.XPATH, xpath_native)

                # Wait for Angular / AJAX options to populate (if options <= 1, wait up to 4s)
                select_obj = Select(dropdown_el)
                if len(select_obj.options) <= 1:
                    for _ in range(8):
                        time.sleep(0.5)
                        try:
                            dropdown_el = driver.find_element(By.XPATH, xpath_native)
                            select_obj = Select(dropdown_el)
                            if len(select_obj.options) > 1:
                                break
                        except Exception:
                            pass

                # 1. First check if target district option is already in the <select> element
                matched_option = None
                matched_value = None
                for opt in select_obj.options:
                    opt_txt = opt.text.strip()
                    opt_val = opt.get_attribute("value")
                    if opt_txt.lower() == target_name.lower() or target_name.lower() in opt_txt.lower():
                        matched_option = opt_txt
                        matched_value = opt_val
                        break
                    if district_code and opt_val == district_code:
                        matched_option = opt_txt
                        matched_value = opt_val
                        break

                if matched_option:
                    try:
                        select_obj.select_by_visible_text(matched_option)
                    except Exception:
                        pass

                    driver.execute_script("""
                        var sel = arguments[0];
                        var val = arguments[1];
                        if (val) sel.value = val;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        sel.dispatchEvent(new Event('input', { bubbles: true }));
                    """, dropdown_el, matched_value)

                    self.logger.info(f"📍 District set to '{matched_option}' (code: {matched_value}).")
                    time.sleep(0.5)
                    return True

                # 2. If dropdown options are not pre-populated (e.g. only ['District']),
                # inject the target district option directly using official district code!
                if district_code:
                    driver.execute_script("""
                        var sel = arguments[0];
                        var code = arguments[1];
                        var name = arguments[2];
                        if (sel && code) {
                            var opt = document.createElement('option');
                            opt.value = code;
                            opt.text = name;
                            opt.selected = true;
                            sel.appendChild(opt);
                            sel.value = code;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            sel.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    """, dropdown_el, district_code, target_name)

                    self.logger.info(f"📍 District set to '{target_name}' (code: {district_code}, selected via search form).")
                    time.sleep(0.5)
                    return True

                current_opts = [o.text.strip() for o in select_obj.options if o.text.strip()]
                self.logger.warning(f"District '{target_name}' not yet in dropdown options ({current_opts[:4]}...). Waiting...")

            except Exception as e:
                err_summary = str(e).split("\n")[0].strip()
                if "Stacktrace:" in err_summary:
                    err_summary = err_summary.split("Stacktrace:")[0].strip()
                self.logger.warning(f"District selection attempt {attempt}/{max_retries} warning: {err_summary}")

            if attempt < max_retries:
                time.sleep(1.5)

        self.logger.error(f"Could not select district '{district_name}' after {max_retries} attempts.")
        return False
        return False

    def select_project_type_radio(self, driver, project_type_category: str) -> bool:
        if not project_type_category:
            return True
        is_revoked = "revoked" in project_type_category.lower()
        target_label = "Revoked Projects" if is_revoked else "Registered Projects"
        try:
            radios = driver.find_elements(
                By.XPATH,
                f"//label[contains(text(), '{target_label}')]/input | "
                f"//input[@type='radio' and (contains(@value, '{'Revoked' if is_revoked else 'Registered'}') or contains(@id, '{'Revoked' if is_revoked else 'Registered'}'))] | "
                f"//label[contains(text(), '{target_label}')]"
            )
            for r in radios:
                if r.is_displayed():
                    driver.execute_script("arguments[0].click();", r)
                    self.logger.info(f"🔘 Selected Project Type: '{target_label}'")
                    time.sleep(0.5)
                    return True
        except Exception as e:
            self.logger.warning(f"Could not select radio '{target_label}': {e}")
        return False

    def fill_search_query(self, driver, query: str) -> bool:
        if not query:
            return True
        target_q = str(query).strip()
        try:
            # Dismiss any popup modal that might block input click
            driver.execute_script("""
                document.querySelectorAll('div.modal.show, div.modal.fade.show').forEach(function(m){
                    m.classList.remove('show'); m.style.display = 'none';
                });
                document.querySelectorAll('.modal-backdrop').forEach(function(b){ b.remove(); });
                document.body.classList.remove('modal-open');
            """)
            inp = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH,
                "//input[contains(translate(@placeholder,'PROJECT NAME','project name'),'project name') "
                "or contains(translate(@placeholder,'REGISTRATION NUMBER','registration number'),'registration number') "
                "or contains(translate(@formcontrolname,'PROJECT','project'),'project') "
                "or @id='projectName' or @name='projectName']"
            )))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", inp)
            inp.clear()
            inp.send_keys(target_q)
            driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, inp, target_q)
            self.logger.info(f"🔎 Set Project Name/RERA ID query: '{target_q}'")
            return True
        except Exception as e:
            self.logger.warning(f"Could not fill search query '{target_q}': {e}")
            return False

    def fill_pincode(self, driver, pincode: str) -> bool:
        if not pincode:
            return True
        target_pin = str(pincode).strip()
        try:
            # Dismiss any popup modal that might block input click
            driver.execute_script("""
                document.querySelectorAll('div.modal.show, div.modal.fade.show').forEach(function(m){
                    m.classList.remove('show'); m.style.display = 'none';
                });
                document.querySelectorAll('.modal-backdrop').forEach(function(b){ b.remove(); });
                document.body.classList.remove('modal-open');
            """)
            pin_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH,
                "//input[contains(translate(@placeholder,'PINCODE','pincode'),'pincode') "
                "or contains(translate(@placeholder,'PIN','pin'),'pin') "
                "or contains(translate(@formcontrolname,'PINCODE','pincode'),'pincode') "
                "or contains(translate(@data-drupal-selector,'LOCATION','location'),'location') "
                "or @id='pincode' or @name='pincode' or @id='pin_code' or @id='edit-project-location']"
            )))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", pin_input)
            pin_input.clear()
            pin_input.send_keys(target_pin)
            driver.execute_script("""
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, pin_input, target_pin)
            self.logger.info(f"📮 Pincode set to '{target_pin}'.")
            return True
        except Exception as e:
            self.logger.warning(f"Could not fill pincode '{target_pin}': {e}")
            return False

    def fill_completion_date(self, driver, date_str: str) -> bool:
        if not date_str:
            return True
        try:
            date_inp = WebDriverWait(driver, 5).until(EC.presence_of_element_located((
                By.XPATH,
                "//input[contains(@placeholder, 'Completion Date') or contains(@formcontrolname, 'completion') "
                "or contains(@id, 'completion') or contains(@name, 'completion')]"
            )))
            date_inp.clear()
            date_inp.send_keys(str(date_str).strip())
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", date_inp)
            self.logger.info(f"📅 Set Completion Date: '{date_str}'")
            return True
        except Exception as e:
            self.logger.warning(f"Could not set completion date '{date_str}': {e}")
            return False

    def click_reset_button(self, driver) -> bool:
        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[normalize-space()='Reset' or contains(translate(., 'RESET', 'reset'), 'reset')]"
            )
            driver.execute_script("arguments[0].click();", btn)
            self.logger.info("🔄 Clicked Reset button on MahaRERA search form.")
            time.sleep(1)
            return True
        except Exception:
            return False

    def click_search_button(self, driver) -> bool:
        candidate_xpaths = [
            "//form[@id='projects-search-page-form']//input[@id='edit-submit' and @type='submit']",
            "//input[@id='edit-submit' and @type='submit']",
            "//form[@id='projects-search-page-form']//input[@type='submit']",
            "//button[normalize-space()='Search']",
            "//button[contains(translate(normalize-space(.),'SEARCH','search'),'search')]",
            "//input[@type='submit' and contains(translate(@value,'SEARCH','search'),'search')]",
            "//a[normalize-space()='Search']",
            "//*[self::button or self::a][contains(translate(normalize-space(.),'SEARCH','search'),'search') and not(contains(translate(normalize-space(.),'RESET','reset'),'reset'))]"
        ]

        for xpath in candidate_xpaths:
            try:
                elements = [el for el in driver.find_elements(By.XPATH, xpath) if el.is_displayed()]
                for el in elements:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", el)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue
        return False

    def check_and_dismiss_no_records_popup(self, driver) -> bool:
        try:
            # If project result cards are already present on the page, records ARE found!
            sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            if sections and len(sections) > 0:
                return False

            indicators = [
                "//div[contains(@class, 'modal') and contains(@class, 'show') and contains(translate(., 'NO RECORDS FOUND', 'no records found'), 'no records found')]",
                "//*[contains(@class, 'modal') and contains(@class, 'show')]//*[contains(translate(text(), 'NO RECORDS FOUND', 'no records found'), 'no records found')]"
            ]
            popup_found = False
            for xpath in indicators:
                try:
                    elements = [el for el in driver.find_elements(By.XPATH, xpath) if el.is_displayed()]
                    if elements:
                        popup_found = True
                        break
                except Exception:
                    continue

            if popup_found:
                self.logger.warning("'Search Record: No Records Found' popup detected! Dismissing and recovering...")
                close_button_xpaths = [
                    "//div[contains(@class,'modal') and contains(@class,'show')]//button[normalize-space()='Close' or contains(translate(.,'CLOSE','close'),'close')]",
                    "//button[normalize-space()='Close']",
                    "//button[contains(translate(normalize-space(.),'CLOSE','close'),'close')]",
                    "//div[contains(@class,'modal')]//button[@data-bs-dismiss='modal']",
                    "//div[contains(@class,'modal')]//button[contains(@class,'btn-close')]"
                ]
                for btn_xp in close_button_xpaths:
                    try:
                        btns = [b for b in driver.find_elements(By.XPATH, btn_xp) if b.is_displayed()]
                        for b in btns:
                            driver.execute_script("arguments[0].click();", b)
                            time.sleep(0.5)
                            break
                    except Exception:
                        pass

                try:
                    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                    driver.execute_script("""
                        document.querySelectorAll('div.modal.show').forEach(function(m){
                            m.classList.remove('show'); m.style.display = 'none';
                        });
                        document.querySelectorAll('.modal-backdrop').forEach(function(b){ b.remove(); });
                        document.body.classList.remove('modal-open');
                    """)
                except Exception:
                    pass
                time.sleep(1)
                return True
        except Exception:
            pass
        return False

    def apply_search_filters_and_search(self, driver, district_name: Optional[str] = None, pincode: Optional[str] = None, max_retries: int = 3) -> bool:
        """Establish search session on MahaRERA by filling all configured search filters and clicking Search."""
        target_district = district_name or self.config.district_name
        target_pincode = pincode or self.config.pincode
        target_query = self.config.search_query
        target_type = self.config.project_type_category
        target_comp_date = self.config.completion_date

        for attempt in range(1, max_retries + 1):
            self.logger.info(f"🔄 Search filter navigation: navigating to {self.config.base_search_url} (attempt {attempt}/{max_retries})...")
            if not self.browser.safe_get(driver, self.config.base_search_url, self.config.refresh_attempts):
                self.logger.warning(f"safe_get failed to reach search page (attempt {attempt}/{max_retries})")
                continue

            # 1. Project Type category (Registered vs Revoked)
            if target_type:
                self.select_project_type_radio(driver, target_type)

            # 2. Select State so District options load in DOM
            self.select_state_dropdown(driver, "Maharashtra")

            # 3. District (select before typing text query to avoid dropdown AJAX reset)
            skip_districts = ("all", "all districts", "all / any district", "select district", "--select district--", "any", "multiple", "")
            if target_district and target_district.strip().lower() not in skip_districts:
                if not self.select_district_dropdown(driver, target_district):
                    self.logger.warning(f"Failed to select district '{target_district}' on attempt {attempt}/{max_retries}.")
                    continue

            # 4. Pincode
            if target_pincode:
                self.fill_pincode(driver, target_pincode)

            # 5. Completion Date
            if target_comp_date:
                self.fill_completion_date(driver, target_comp_date)

            # 6. Search query (Project Name / MahaRERA Registration Number)
            if target_query:
                self.fill_search_query(driver, target_query)

            # 7. Click Search
            if not self.click_search_button(driver):
                self.logger.warning(f"Could not click Search button (attempt {attempt}/{max_retries})")
                continue

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded"
                    ))
                )
            except TimeoutException:
                pass

            sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            if sections and len(sections) > 0:
                self.browser.set_driver_current_page(driver, 1)
                self.logger.info(f"✅ Landed on results page 1 via search filters ({len(sections)} sections visible).")
                return True

            if self.check_and_dismiss_no_records_popup(driver):
                self.logger.info(f"ℹ️ 'No Records Found' returned for specified search criteria.")
                return False

        return False

    def detect_pagination_info(self, driver) -> Tuple[Optional[int], Optional[int]]:
        """Extract total results and total pages from MahaRERA search results page.
        Returns: (total_records, total_pages)
        """
        total_records: Optional[int] = None
        total_pages: Optional[int] = None

        try:
            # 1. Search for div.pagination attributes and text (MahaRERA native)
            pag_spans = driver.find_elements(By.CSS_SELECTOR, "div.pagination span.pagesCount, span.pagesCount")
            for sp in pag_spans:
                data_tot = sp.get_attribute("data-total")
                data_pages = sp.get_attribute("data-current-data")
                if data_tot and data_tot.isdigit() and int(data_tot) > 0:
                    total_records = int(data_tot)
                    total_pages = int(data_pages) if data_pages and data_pages.isdigit() else max(1, math.ceil(total_records / 10))
                    self.logger.info(f"📊 Detected pagination from div.pagination attributes: {total_records} total records ({total_pages} pages).")
                    return total_records, total_pages

            pag_divs = driver.find_elements(By.CSS_SELECTOR, "div.pagination")
            for pd in pag_divs:
                t = pd.text.strip()
                m = re.search(r'of\s+(\d+)', t, re.IGNORECASE)
                if m:
                    total_pages = int(m.group(1))
                    total_records = total_pages * 10
                    self.logger.info(f"📊 Detected pagination from div.pagination text: {total_records} total records ({total_pages} pages).")
                    return total_records, total_pages

            # 2. Search for text like "Showing Final 2 Result" or "Showing 1 to 10 of 1450 Result"
            elements = driver.find_elements(
                By.XPATH,
                "//*[contains(normalize-space(.), 'Showing') and contains(normalize-space(.), 'Result')]"
            )
            for el in elements:
                txt = el.text.strip()
                if not txt:
                    continue
                # Match "Showing Final 2 Result"
                m_final = re.search(r'Showing\s+Final\s+(\d+)\s+Result', txt, re.IGNORECASE)
                if m_final:
                    total_records = int(m_final.group(1))
                    total_pages = max(1, math.ceil(total_records / 10))
                    self.logger.info(f"📊 Detected pagination from results header: {total_records} total records ({total_pages} pages).")
                    return total_records, total_pages

                # Match "Showing 1 to 10 of 1450 Result" or "of 450 Result"
                m_of = re.search(r'of\s+(\d+)\s+Result', txt, re.IGNORECASE)
                if m_of:
                    total_records = int(m_of.group(1))
                    total_pages = max(1, math.ceil(total_records / 10))
                    self.logger.info(f"📊 Detected pagination from results header: {total_records} total records ({total_pages} pages).")
                    return total_records, total_pages

            # 3. Check pagination-controls or pagination links
            page_links = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'pagination')]//a | //pagination-controls//a | //ul[contains(@class,'pagination')]//a | //li[contains(@class,'page-item')]//a"
            )
            max_p = 1
            for pl in page_links:
                t = pl.text.strip()
                if t.isdigit():
                    max_p = max(max_p, int(t))
            if max_p > 1:
                total_pages = max_p
                total_records = max_p * 10
                self.logger.info(f"📊 Detected pagination from nav buttons: at least {total_pages} pages.")
                return total_records, total_pages

        except Exception as e:
            self.logger.debug(f"Pagination detection error: {e}")

        return total_records, total_pages

    def extract_canonical_url_template(self, driver) -> Optional[str]:
        """Extract canonical search URL template from pagination elements on the page."""
        try:
            # 1. From div.pagination a.next
            next_links = driver.find_elements(By.CSS_SELECTOR, "div.pagination a.next, a.next")
            for nl in next_links:
                href = nl.get_attribute("href")
                if href and "page=" in href:
                    self.canonical_page_url_template = re.sub(r'page=\d+', 'page=__PAGE__', href)
                    self.logger.debug(f"Captured canonical URL template from a.next: {self.canonical_page_url_template}")
                    return self.canonical_page_url_template

            # 2. From div.pagination a.prev
            prev_links = driver.find_elements(By.CSS_SELECTOR, "div.pagination a.prev, a.prev")
            for pl in prev_links:
                href = pl.get_attribute("href")
                if href and "page=" in href:
                    self.canonical_page_url_template = re.sub(r'page=\d+', 'page=__PAGE__', href)
                    self.logger.debug(f"Captured canonical URL template from a.prev: {self.canonical_page_url_template}")
                    return self.canonical_page_url_template

            # 3. From select-project-pagination onchange script
            sel_pags = driver.find_elements(By.ID, "select-project-pagination")
            if sel_pags:
                onch = sel_pags[0].get_attribute("onchange") or ""
                m = re.search(r'location\.href\s*=\s*["\'](https?://[^"\']+)["\']\s*\+\s*this\.value\s*\+\s*["\']([^"\']+)["\']', onch)
                if m:
                    self.canonical_page_url_template = f"{m.group(1)}__PAGE__{m.group(2)}"
                    self.logger.debug(f"Captured canonical URL template from select pagination: {self.canonical_page_url_template}")
                    return self.canonical_page_url_template
        except Exception as e:
            self.logger.debug(f"Could not extract canonical URL template: {e}")
        return None

    def build_page_url(self, page_number: int) -> str:
        # Use canonical URL template captured from MahaRERA search results if available
        if self.canonical_page_url_template:
            return self.canonical_page_url_template.replace("page=__PAGE__", f"page={page_number}")

        # Resolve district code from name if missing
        if not self.config.district_code and self.config.district_name:
            d_clean = self.config.district_name.strip().lower()
            if d_clean in MAHARASHTRA_DISTRICT_CODE_MAP:
                self.config.district_code = MAHARASHTRA_DISTRICT_CODE_MAP[d_clean]

        q_name = urllib.parse.quote_plus(self.config.search_query.strip()) if self.config.search_query else ""
        q_dist = urllib.parse.quote_plus(self.config.district_code.strip()) if self.config.district_code else "0"
        q_state = urllib.parse.quote_plus(self.config.project_state.strip()) if self.config.project_state else "27"
        q_pin = urllib.parse.quote_plus(self.config.pincode.strip()) if self.config.pincode else ""
        q_date = urllib.parse.quote_plus(self.config.completion_date.strip()) if self.config.completion_date else ""
        q_div = urllib.parse.quote_plus(self.config.division.strip()) if self.config.division else ""
        loc_val = urllib.parse.quote_plus(self.config.locality.strip()) if self.config.locality else ""

        # MahaRERA expects pincode in project_location parameter if locality is empty!
        if not loc_val and q_pin:
            loc_val = q_pin

        q_type = "RevokedProjects" if "revoked" in self.config.project_type_category.lower() else "RegisteredProjects"

        return (
            f"{self.config.base_search_url}"
            f"?project_name={q_name}"
            f"&project_location={loc_val}"
            f"&project_completion_date={q_date}"
            f"&project_state={q_state}"
            f"&project_district={q_dist}"
            f"&project_type={q_type}"
            f"&carpetAreas=&completionPercentages=&project_division={q_div}"
            f"&page={page_number}&op=Search"
        )

    def step_next_page(self, driver, expected_page: int) -> bool:
        """Advance sequentially to expected_page via div.pagination a.next button."""
        try:
            next_btns = driver.find_elements(By.CSS_SELECTOR, "div.pagination a.next, a.next")
            if not next_btns:
                self.logger.info(f"🏁 Next button not found. Target page {expected_page} is beyond available results.")
                self.is_last_page_reached = True
                return False
            next_btn = next_btns[0]
            cls = next_btn.get_attribute("class") or ""
            if "disabled" in cls.lower():
                self.logger.info(f"🏁 Next button is disabled. Target page {expected_page} is beyond available results.")
                self.is_last_page_reached = True
                return False

            driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", next_btn)
            try:
                WebDriverWait(driver, 20).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "div.pagination span.pagesCount").text.strip() == str(expected_page)
                )
            except TimeoutException:
                pass

            cards = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            cur_p = None
            try:
                sp = driver.find_elements(By.CSS_SELECTOR, "div.pagination span.pagesCount, span.pagesCount")
                if sp and sp[0].text.strip().isdigit():
                    cur_p = int(sp[0].text.strip())
            except Exception:
                pass

            if (cur_p == expected_page or cur_p is None) and len(cards) > 0:
                self.browser.set_driver_current_page(driver, expected_page)
                self.extract_canonical_url_template(driver)
                self.logger.info(f"✅ Successfully stepped to page {expected_page} ({len(cards)} project cards visible).")
                return True
        except Exception as e:
            self.logger.warning(f"step_next_page warning: {e}")
        return False

    def go_to_results_page(self, driver, target_page: int, refresh_on_fail: bool = True) -> bool:
        self.is_last_page_reached = False  # Always reset flag at start of new page navigation

        # 1. Check live DOM and recorded page state
        current_page = self.browser.get_driver_current_page(driver)
        dom_p = None
        try:
            sp = driver.find_elements(By.CSS_SELECTOR, "div.pagination span.pagesCount, span.pagesCount")
            if sp and sp[0].text.strip().isdigit():
                dom_p = int(sp[0].text.strip())
                current_page = dom_p
                self.browser.set_driver_current_page(driver, dom_p)
        except Exception:
            pass

        sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
        has_results_dom = (sections and len(sections) > 0) or bool(driver.find_elements(By.CSS_SELECTOR, "div.pagination"))

        if current_page == target_page and sections and len(sections) > 0:
            self.logger.info(f"✅ Driver already on page {target_page} ({len(sections)} sections visible).")
            return True

        # 2. Only if search results are NOT in DOM at all do we re-establish session via search form
        if not has_results_dom:
            self.logger.info(f"🔎 Establishing search session via form filters to reach page {target_page}...")
            if not self.apply_search_filters_and_search(driver):
                self.logger.error("Could not establish search session via search form filters.")
                return False
            current_page = 1
            self.browser.set_driver_current_page(driver, 1)

        # If target is page 1, we are already there!
        if target_page == 1:
            self.extract_canonical_url_template(driver)
            self.browser.set_driver_current_page(driver, 1)
            return True

        # 3. For target_page > 1: Read current page from live DOM
        cur_p = None
        try:
            sp = driver.find_elements(By.CSS_SELECTOR, "div.pagination span.pagesCount, span.pagesCount")
            if sp and sp[0].text.strip().isdigit():
                cur_p = int(sp[0].text.strip())
        except Exception:
            pass
        if cur_p is None:
            cur_p = getattr(driver, "_current_page", 1)

        # Case A: We are behind target_page -> Advance sequentially inside the live search session
        if cur_p is not None and cur_p < target_page:
            while cur_p < target_page:
                next_target = cur_p + 1

                # Check if direct link for target_page is directly clickable in pagination bar
                direct_links = driver.find_elements(
                    By.XPATH,
                    f"//div[contains(@class,'pagination')]//a[normalize-space()='{target_page}'] | "
                    f"//ul[contains(@class,'pagination')]//a[normalize-space()='{target_page}']"
                )
                if direct_links and direct_links[0].is_displayed() and next_target != target_page:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", direct_links[0])
                        time.sleep(2)
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded"))
                        )
                        self.browser.set_driver_current_page(driver, target_page)
                        self.logger.info(f"🎯 Jumped directly to page {target_page} via pagination number link.")
                        return True
                    except Exception:
                        pass

                self.logger.info(f"🖱️ Advancing sequentially from page {cur_p} to page {next_target} (target: {target_page})...")
                if not self.step_next_page(driver, next_target):
                    if self.is_last_page_reached:
                        self.logger.info(f"🏁 Reached end of available search results at page {cur_p}. Cannot advance to page {target_page}.")
                        return False
                    self.logger.warning(f"Could not advance step from page {cur_p} to {next_target}.")
                    break
                cur_p = next_target

            if cur_p == target_page:
                return True

        # Case B: We are ahead of target_page (e.g. retry after jump) -> Re-establish from page 1 and step forward
        if cur_p is not None and cur_p > target_page:
            self.logger.info(f"🔄 Current page {cur_p} is ahead of target page {target_page}. Re-establishing from page 1...")
            if not self.apply_search_filters_and_search(driver):
                return False
            cur_p = 1
            self.browser.set_driver_current_page(driver, 1)
            while cur_p < target_page:
                next_target = cur_p + 1
                if not self.step_next_page(driver, next_target):
                    return False
                cur_p = next_target
            if cur_p == target_page:
                return True

        self.browser.reset_driver_page_state(driver)
        self.logger.error(f"❌ Failed go_to_results_page: could not reach page {target_page}.")
        return False

