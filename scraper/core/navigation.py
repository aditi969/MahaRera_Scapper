"""Search navigation, district filtering, and pagination for MahaRERA search.

Matches exact logic and selectors from Cell 3 of RERA_Scrapping_fixed_v3.ipynb.
"""
import time
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from scraper.core.browser import BrowserManager
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


class NavigationManager:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger, browser: BrowserManager):
        self.config = config
        self.logger = logger
        self.browser = browser

    def select_district_dropdown(self, driver, district_name: str, max_retries: int = 3) -> bool:
        if not district_name:
            return True

        target_name = district_name.strip()
        xpath_native = (
            "//select[contains(translate(@formcontrolname,'DISTRICT','district'),'district') "
            "or contains(translate(@id,'DISTRICT','district'),'district') "
            "or contains(translate(@name,'DISTRICT','district'),'district')]"
        )

        for attempt in range(1, max_retries + 1):
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, xpath_native)))
                dropdown_el = driver.find_element(By.XPATH, xpath_native)

                def check_options(d):
                    try:
                        el = d.find_element(By.XPATH, xpath_native)
                        s = Select(el)
                        opts = [o.text.strip() for o in s.options if o.text and o.text.strip()]
                        return len(opts) > 3 or any(target_name.lower() in o.lower() for o in opts)
                    except Exception:
                        return False

                try:
                    WebDriverWait(driver, 20, poll_frequency=1).until(check_options)
                except TimeoutException:
                    pass

                select_obj = Select(dropdown_el)
                matched_option = None
                matched_value = None
                for opt in select_obj.options:
                    opt_txt = opt.text.strip()
                    if opt_txt.lower() == target_name.lower() or target_name.lower() in opt_txt.lower():
                        matched_option = opt_txt
                        matched_value = opt.get_attribute("value")
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

                    self.logger.info(f"📍 District set to '{matched_option}' (native <select>).")
                    time.sleep(1)
                    return True
                else:
                    current_opts = [o.text.strip() for o in select_obj.options if o.text.strip()]
                    self.logger.warning(f"District '{target_name}' not yet in dropdown options ({current_opts[:4]}...). Waiting...")

            except Exception as e:
                self.logger.warning(f"District selection attempt {attempt}/{max_retries} warning: {e}")

            try:
                custom_control = driver.find_elements(By.XPATH, "(//ng-select | //div[contains(@class,'ng-select')])[1]")
                if custom_control and custom_control[0].is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", custom_control[0])
                    custom_control[0].click()
                    time.sleep(0.5)
                    opt = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((
                        By.XPATH, f"//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{target_name.lower()}')]"
                    )))
                    opt.click()
                    self.logger.info(f"📍 District set to '{target_name}' (custom dropdown).")
                    return True
            except Exception:
                pass

            if attempt < max_retries:
                time.sleep(3)
                try:
                    if self.browser.driver_is_alive(driver):
                        driver.refresh()
                        time.sleep(self.config.page_load_wait)
                except Exception:
                    pass

        self.logger.error(f"Could not select district '{district_name}' after {max_retries} attempts.")
        return False

    def fill_pincode(self, driver, pincode: str) -> bool:
        if not pincode:
            return True
        try:
            pin_input = driver.find_element(
                By.XPATH,
                "//input[contains(@placeholder,'Pincode') or contains(@placeholder,'PIN') "
                "or contains(translate(@formcontrolname,'PINCODE','pincode'),'pincode')]"
            )
            pin_input.clear()
            pin_input.send_keys(str(pincode))
            self.logger.info(f"📮 Pincode set to '{pincode}'.")
            return True
        except Exception:
            return False

    def click_search_button(self, driver) -> bool:
        candidate_xpaths = [
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
        """Fallback to establish search session on MahaRERA by filling district and clicking Search."""
        target_district = district_name or self.config.district_name
        target_pincode = pincode or self.config.pincode

        for attempt in range(1, max_retries + 1):
            self.logger.info(f"🔄 Search filter fallback: navigating to {self.config.base_search_url} (attempt {attempt}/{max_retries})...")
            if not self.browser.safe_get(driver, self.config.base_search_url, self.config.refresh_attempts):
                self.logger.warning(f"safe_get failed to reach search page (attempt {attempt}/{max_retries})")
                continue

            if not self.select_district_dropdown(driver, target_district):
                self.logger.warning(f"Failed to select district '{target_district}' on attempt {attempt}/{max_retries}.")
                continue

            if target_pincode:
                self.fill_pincode(driver, target_pincode)

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
                self.logger.info(f"✅ Landed on results page 1 via district search filters ({len(sections)} sections visible).")
                return True

            if self.check_and_dismiss_no_records_popup(driver):
                self.logger.info(f"🔄 'No Records Found' after search (attempt {attempt}/{max_retries}). Retrying search...")
                continue

        return False

    def build_page_url(self, page_number: int) -> str:
        return (
            f"{self.config.base_search_url}"
            f"?project_name=&project_location=&project_completion_date="
            f"&project_state={self.config.project_state}"
            f"&project_district={self.config.district_code}"
            f"&carpetAreas=&completionPercentages=&project_division="
            f"&page={page_number}&op=Search"
        )

    def go_to_results_page(self, driver, target_page: int, refresh_on_fail: bool = True) -> bool:
        max_nav_attempts = 2 if refresh_on_fail else 1

        for attempt in range(1, max_nav_attempts + 1):
            page_url = self.build_page_url(target_page)
            self.logger.info(f"Link Navigating directly to page {target_page} via URL (attempt {attempt}/{max_nav_attempts}): {page_url}")

            if not self.browser.safe_get(driver, page_url, self.config.refresh_attempts):
                self.logger.warning(f"safe_get failed for page {target_page} URL (attempt {attempt}/{max_nav_attempts})")
                time.sleep(self.config.retry_backoff_seconds)
                continue

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//div[contains(@class,'row') and contains(@class,'shadow')] | "
                        "//pagination-controls | //ul[contains(@class,'pagination')] | "
                        "//div[contains(@class,'modal') and contains(@class,'show')]"
                    ))
                )
            except TimeoutException:
                pass

            # Check if project cards exist first!
            sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            if sections and len(sections) > 0:
                self.browser.set_driver_current_page(driver, target_page)
                self.logger.info(f"Success Successfully landed on page {target_page} via direct URL ({len(sections)} sections visible).")
                return True

            if self.check_and_dismiss_no_records_popup(driver):
                self.logger.info(f"Retry No Records Found on page {target_page} URL. Retrying (attempt {attempt}/{max_nav_attempts})...")
                time.sleep(self.config.retry_backoff_seconds)
                continue

            sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            if sections and len(sections) > 0:
                self.browser.set_driver_current_page(driver, target_page)
                self.logger.info(f"Success Successfully landed on page {target_page} via direct URL.")
                return True

        # Fallback for page 1 if direct URL navigation failed:
        if target_page == 1:
            self.logger.info("🔄 Direct URL navigation to page 1 failed. Falling back to form search filters...")
            if self.apply_search_filters_and_search(driver):
                return True

        self.browser.reset_driver_page_state(driver)
        self.logger.error(f"Failed go_to_results_page: failed to reach page {target_page} after {max_nav_attempts} attempts.")
        return False

