"""Adaptive driver management and safe navigation for MahaRERA scraper.

Matches exact settings and recovery logic from Cell 3 of RERA_Scrapping_fixed_v3.ipynb.
"""
import random
import threading
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger

thread_local_storage = threading.local()


class BrowserManager:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger):
        self.config = config
        self.logger = logger
        self._driver_current_page = {}
        self._driver_page_state_lock = threading.Lock()

    def create_driver(self, headless: Optional[bool] = None) -> webdriver.Chrome:
        if headless is None:
            headless = self.config.headless

        options = Options()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-popup-blocking")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.page_load_strategy = "normal"

        prefs = {
            "plugins.always_open_pdf_externally": False,
            "profile.default_content_settings.popups": 0,
            "download.prompt_for_download": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        return driver

    def driver_is_alive(self, driver: Optional[webdriver.Chrome]) -> bool:
        if driver is None:
            return False
        try:
            driver.execute_script("return 1")
            return True
        except Exception:
            return False

    def get_thread_driver(self) -> webdriver.Chrome:
        if not hasattr(thread_local_storage, "driver") or thread_local_storage.driver is None:
            self.logger.info("🌐 Initializing dedicated Chrome WebDriver for worker thread...")
            thread_local_storage.driver = self.create_driver(self.config.headless)
        else:
            if not self.driver_is_alive(thread_local_storage.driver):
                self.logger.warning("💥 Thread driver was disconnected or died — restarting Chrome...")
                try:
                    thread_local_storage.driver.quit()
                except Exception:
                    pass
                thread_local_storage.driver = self.create_driver(self.config.headless)
        return thread_local_storage.driver

    def close_thread_driver(self):
        if hasattr(thread_local_storage, "driver") and thread_local_storage.driver is not None:
            try:
                thread_local_storage.driver.quit()
            except Exception:
                pass
            thread_local_storage.driver = None

    def safe_get(self, driver: webdriver.Chrome, url: str, refresh_attempts: Optional[int] = None) -> bool:
        if refresh_attempts is None:
            refresh_attempts = self.config.refresh_attempts

        for attempt in range(1, refresh_attempts + 2):
            try:
                if not self.driver_is_alive(driver):
                    return False
                driver.get(url)
                time.sleep(self.config.page_load_wait)
                ready_state = driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    return True
            except (TimeoutException, WebDriverException) as e:
                self.logger.warning(f"Navigation issue (attempt {attempt}): {e}")
            
            wait_s = self.config.retry_backoff_seconds * attempt + random.uniform(0, 2)
            self.logger.info(f"🔄 Retrying page load in {wait_s:.1f}s (attempt {attempt}/{refresh_attempts + 1})...")
            time.sleep(wait_s)
            try:
                if self.driver_is_alive(driver):
                    driver.refresh()
                    time.sleep(self.config.page_load_wait)
            except Exception:
                pass
        return False

    def _driver_key(self, driver: webdriver.Chrome) -> str:
        try:
            return driver.session_id or str(id(driver))
        except Exception:
            return str(id(driver))

    def reset_driver_page_state(self, driver: Optional[webdriver.Chrome] = None):
        with self._driver_page_state_lock:
            if driver is not None:
                self._driver_current_page.pop(self._driver_key(driver), None)
            else:
                self._driver_current_page.clear()

    def set_driver_current_page(self, driver: webdriver.Chrome, page: int):
        with self._driver_page_state_lock:
            self._driver_current_page[self._driver_key(driver)] = page

    def get_driver_current_page(self, driver: webdriver.Chrome) -> int:
        with self._driver_page_state_lock:
            return self._driver_current_page.get(self._driver_key(driver), 1)

