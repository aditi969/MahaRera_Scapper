"""Multithreaded page and project scraping engine with real-time progress callbacks.

Matches exact workflow, ThreadPoolExecutor, and failure policies
from Cells 6 and 7 of RERA_Scrapping_fixed_v3.ipynb.
"""
import os
import random
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from scraper.core.browser import BrowserManager
from scraper.core.captcha import CaptchaSolver
from scraper.core.certificate import CertificateExtractor
from scraper.core.checkpoint import CheckpointManager
from scraper.core.config import ScraperConfig
from scraper.core.csv_writer import CsvWriter
from scraper.core.extractor import ProjectExtractor
from scraper.core.logger import ScraperLogger
from scraper.core.navigation import NavigationManager


class ScraperWorker:
    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        logger: Optional[ScraperLogger] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_record_scraped: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.config = config or ScraperConfig()
        self.logger = logger or ScraperLogger(log_file=self.config.run_log_file)
        self.on_progress = on_progress
        self.on_record_scraped = on_record_scraped

        self.browser_manager = BrowserManager(self.config, self.logger)
        self.checkpoint_manager = CheckpointManager(self.config, self.logger)
        self.navigation_manager = NavigationManager(self.config, self.logger, self.browser_manager)
        self.captcha_solver = CaptchaSolver(self.config, self.logger)
        self.cert_extractor = CertificateExtractor(self.config, self.logger)
        self.project_extractor = ProjectExtractor(self.config, self.logger, self.cert_extractor)
        self.csv_writer = CsvWriter(self.config, self.logger)

    def _notify_progress(self, event_type: str, data: Dict[str, Any]):
        if self.on_progress:
            try:
                payload = {"type": event_type, "timestamp": time.time(), **data}
                self.on_progress(payload)
            except Exception:
                pass

    def scrape_single_project_task(
        self,
        task_info: Dict[str, Any],
        checkpoint_data: Dict[str, Any],
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[bool, Optional[pd.DataFrame]]:
        page_number = task_info["page_number"]
        idx = task_info["project_index"]
        project_url = task_info["project_url"]
        organization = task_info["organization"]
        last_modified = task_info["last_modified"]

        if cancel_event and cancel_event.is_set():
            return False, None

        if self.checkpoint_manager.is_project_already_scraped(checkpoint_data, project_url):
            self.logger.info(f"⏩ Project {idx + 1} on page {page_number} ({project_url}) already scraped — skipping.")
            return True, None

        self.logger.info(f"🚀 Opening project {idx + 1} on page {page_number}: {project_url}")

        for attempt in range(1, self.config.max_project_retries + 1):
            if cancel_event and cancel_event.is_set():
                return False, None

            driver = self.browser_manager.get_thread_driver()

            try:
                self.checkpoint_manager.record_interrupted_project(
                    checkpoint_data, page_number, idx, project_url, reason="in_progress"
                )

                driver.get(project_url)
                driver.execute_script("document.body.style.zoom='75%'")

                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "captcahCanvas")))
                except TimeoutException:
                    pass

                captcha_img_file = f"captcha_p{page_number}_i{idx}_t{threading.get_ident()}.png"
                captcha_ok = self.captcha_solver.solve_captcha_fully_automated(driver, captcha_img_file)

                if os.path.exists(captcha_img_file):
                    try:
                        os.remove(captcha_img_file)
                    except Exception:
                        pass

                if not captcha_ok:
                    raise Exception("Captcha solve failed after retries")

                df = self.project_extractor.extract_project_data(driver)
                df["Organization"] = organization
                df["Last_Modified"] = last_modified
                df["source_url"] = project_url

                cert_dates = self.cert_extractor.get_cert_dates_with_retries(driver)
                for _k, _v in cert_dates.items():
                    df[_k] = _v

                rera_id = None
                if "Registration Number" in df.columns and len(df["Registration Number"]) > 0:
                    rera_id = df["Registration Number"].iloc[0]

                if rera_id and str(rera_id).strip() in self.checkpoint_manager.load_existing_csv_rera_ids():
                    self.logger.info(f"RERA ID {rera_id} already in {self.config.output_csv} -- marking completed.")
                    self.checkpoint_manager.mark_project_completed(checkpoint_data, project_url, rera_id=rera_id)
                    return True, None

                with self.checkpoint_manager.csv_lock:
                    saved_df = self.csv_writer.save_scraped_project_row(df, self.config.output_csv, limit=self.config.excel_char_limit)

                self.checkpoint_manager.add_scraped_id_to_cache(rera_id)
                self.checkpoint_manager.mark_project_completed(checkpoint_data, project_url, rera_id=rera_id)
                self.logger.info(f"Project {idx + 1} on page {page_number} scraped successfully! (RERA ID: {rera_id})")

                # Ingestion callback
                if self.on_record_scraped and not df.empty:
                    try:
                        row_dict = df.iloc[0].to_dict()
                        self.on_record_scraped(row_dict)
                    except Exception as ing_e:
                        self.logger.warning(f"Error in on_record_scraped callback: {ing_e}")

                self._notify_progress("project_extracted", {
                    "page": page_number,
                    "project_index": idx,
                    "rera_id": rera_id,
                    "project_name": df["Project Name"].iloc[0] if "Project Name" in df.columns else ""
                })

                return True, saved_df

            except Exception as e:
                err_msg = str(e)
                self.logger.warning(f"Project {idx + 1} on page {page_number} (attempt {attempt}/{self.config.max_project_retries}) error: {err_msg}")
                self.checkpoint_manager.record_interrupted_project(
                    checkpoint_data, page_number, idx, project_url, reason=f"error_{attempt}: {err_msg}"
                )

                if "invalid session id" in err_msg.lower() or "disconnected" in err_msg.lower() or "no such window" in err_msg.lower():
                    self.logger.warning("💥 Browser session closed/disconnected — restarting driver for thread...")
                    self.browser_manager.close_thread_driver()

                if attempt < self.config.max_project_retries:
                    time.sleep(self.config.retry_backoff_seconds * attempt + random.uniform(1, 2))

        self.logger.error(f"Project {idx + 1} on page {page_number} failed permanently after {self.config.max_project_retries} attempts.")
        self.checkpoint_manager.log_failed_project(page_number, idx, project_url, f"Failed after {self.config.max_project_retries} retries")
        self._notify_progress("project_failed", {
            "page": page_number,
            "project_index": idx,
            "project_url": project_url,
            "error": f"Failed after {self.config.max_project_retries} retries"
        })
        return False, None

    def fetch_page_project_tasks(
        self,
        driver,
        page_number: int,
        checkpoint_data: Dict[str, Any],
        max_projects_per_page: int = 10,
        max_retries: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if max_retries is None:
            max_retries = self.config.max_page_retries

        for attempt in range(1, max_retries + 1):
            if not self.navigation_manager.go_to_results_page(driver, page_number, refresh_on_fail=True):
                self.logger.warning(f"Could not load search result page {page_number} (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(self.config.retry_backoff_seconds)
                continue

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded"))
                )
            except TimeoutException:
                if self.navigation_manager.check_and_dismiss_no_records_popup(driver):
                    self.logger.info(f"🔄 'No Records Found' popup appeared on page {page_number}. Refreshing...")
                    self.browser_manager.reset_driver_page_state(driver)
                else:
                    self.logger.warning(f"Project sections did not appear on page {page_number} within timeout.")
                    self.browser_manager.reset_driver_page_state(driver)
                if attempt < max_retries:
                    time.sleep(self.config.retry_backoff_seconds)
                continue

            sections = driver.find_elements(By.CSS_SELECTOR, "div.row.shadow.p-3.mb-5.bg-body.rounded")
            if not sections:
                self.logger.warning(f"0 project sections found on page {page_number} (attempt {attempt}/{max_retries}).")
                self.browser_manager.reset_driver_page_state(driver)
                if attempt < max_retries:
                    time.sleep(self.config.retry_backoff_seconds)
                continue

            project_count = min(len(sections), max_projects_per_page)
            self.logger.info(f"Found {len(sections)} project sections on page {page_number} (preparing tasks for {project_count})")

            tasks = []
            for idx in range(project_count):
                section = sections[idx]
                try:
                    try:
                        organization = section.find_element(By.XPATH, ".//p[@class='darkBlue bold ']").text.strip()
                    except Exception:
                        organization = None
                    try:
                        last_modified = section.find_element(
                            By.XPATH, ".//div[@class='greyColor' and text()='Last Modified']/following-sibling::p"
                        ).text.strip()
                    except Exception:
                        last_modified = None

                    view_details_link = section.find_element(By.LINK_TEXT, "View Details")
                    href_value = view_details_link.get_attribute("href")

                    tasks.append({
                        "page_number": page_number,
                        "project_index": idx,
                        "project_url": href_value,
                        "organization": organization,
                        "last_modified": last_modified
                    })
                except Exception as e:
                    self.logger.warning(f"Error preparing task for project {idx + 1} on page {page_number}: {e}")

            if tasks:
                return tasks

        self.logger.error(f"Failed to fetch project tasks for page {page_number} after {max_retries} attempts.")
        return []

    def run_scrape(
        self,
        page_start: Optional[int] = None,
        page_end: Optional[int] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> pd.DataFrame:
        if page_start is None:
            page_start = self.config.start_page
        if page_end is None:
            page_end = self.config.end_page

        checkpoint_data = self.checkpoint_manager.load_checkpoint()
        checkpoint_data["job_start_page"] = min(checkpoint_data.get("job_start_page", page_start), page_start)
        self.checkpoint_manager.save_checkpoint_data(checkpoint_data)
        start_page = checkpoint_data["job_start_page"]

        if start_page != page_start:
            self.logger.info(f"Resuming from Page {start_page} (checkpoint floor) in sequence.")

        master_driver = self.browser_manager.create_driver(self.config.headless)
        combined_df = pd.DataFrame()
        consecutive_page_failures = 0

        self._notify_progress("job_started", {
            "start_page": start_page,
            "end_page": page_end,
            "district": self.config.district_name
        })

        try:
            for page in range(start_page, page_end):
                if cancel_event and cancel_event.is_set():
                    self.logger.info("🛑 Scrape job cancellation detected.")
                    break

                completed_pages = checkpoint_data.get("completed_pages", [])
                if page in completed_pages:
                    self.logger.info(f"⏩ Page {page} already completed — skipping.")
                    continue

                if not self.browser_manager.driver_is_alive(master_driver):
                    self.logger.warning("💥 Master browser session died — restarting Chrome...")
                    try:
                        master_driver.quit()
                    except Exception:
                        pass
                    master_driver = self.browser_manager.create_driver(self.config.headless)
                    self.browser_manager.reset_driver_page_state(master_driver)
                    consecutive_page_failures = 0

                self.logger.info(f"➡️ Processing Page {page}/{page_end - 1}...")
                self._notify_progress("page_started", {"page": page})

                tasks = self.fetch_page_project_tasks(master_driver, page, checkpoint_data)
                if not tasks:
                    consecutive_page_failures += 1
                    self.checkpoint_manager.log_failed_page(page, "Failed to load/parse search results page")

                    if consecutive_page_failures >= self.config.restart_driver_on_consecutive_failures:
                        self.logger.warning(f"🔄 {consecutive_page_failures} consecutive page failures. Restarting master driver...")
                        try:
                            master_driver.quit()
                        except Exception:
                            pass
                        master_driver = self.browser_manager.create_driver(self.config.headless)
                        self.browser_manager.reset_driver_page_state(master_driver)
                        consecutive_page_failures = 0

                    if not self.config.skip_failed_pages:
                        self.logger.info("Stopping run as skip_failed_pages is False.")
                        break
                    continue

                consecutive_page_failures = 0

                active_tasks = [
                    t for t in tasks
                    if not self.checkpoint_manager.is_project_already_scraped(checkpoint_data, t["project_url"])
                ]
                skipped_count = len(tasks) - len(active_tasks)
                if skipped_count:
                    self.logger.info(f"⏩ Skipping {skipped_count} already-scraped project(s) on page {page}.")

                if not active_tasks:
                    self.logger.info(f"✅ All projects on page {page} already processed.")
                    self.checkpoint_manager.mark_page_completed(checkpoint_data, page)
                    self._notify_progress("page_completed", {"page": page})
                    continue

                self.logger.info(f"⚡ Launching ThreadPoolExecutor with {self.config.max_workers} workers for {len(active_tasks)} project tasks on page {page}...")

                page_results = []
                with ThreadPoolExecutor(max_workers=self.config.max_workers, thread_name_prefix="ScraperWorker") as executor:
                    future_to_task = {
                        executor.submit(self.scrape_single_project_task, task, checkpoint_data, cancel_event): task
                        for task in active_tasks
                    }

                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        try:
                            success, df = future.result()
                            if success and df is not None:
                                page_results.append(df)
                        except Exception as exc:
                            self.logger.warning(f"💥 Worker exception on project {task['project_index'] + 1}: {exc}")

                if page_results:
                    page_df = pd.concat(page_results, ignore_index=True)
                    combined_df = pd.concat([combined_df, page_df], ignore_index=True)

                still_missing = [
                    t for t in tasks
                    if not self.checkpoint_manager.is_project_already_scraped(checkpoint_data, t["project_url"])
                ]
                if not still_missing:
                    self.checkpoint_manager.mark_page_completed(checkpoint_data, page)
                    self.logger.info(f"🏁 Completed processing page {page}.")
                    self._notify_progress("page_completed", {"page": page})
                else:
                    self.logger.warning(f"Page {page} has {len(still_missing)} project(s) still unscraped.")
                    if not self.config.skip_failed_projects:
                        self.logger.info("Stopping run as skip_failed_projects is False.")
                        break

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("🛑 Manual Interrupt received! Progress recorded in checkpoint.")
        except Exception as exc:
            self.logger.error(f"Unexpected error in run loop: {exc}")
            self.logger.error(traceback.format_exc())
        finally:
            self.logger.info("🧹 Cleaning up master browser session...")
            try:
                master_driver.quit()
            except Exception:
                pass
            self.browser_manager.close_thread_driver()

        if self.config.auto_export_excel and not combined_df.empty:
            self.csv_writer.export_and_verify_dataset(
                self.config.output_csv, self.config.output_xlsx, limit=self.config.excel_char_limit
            )

        self._notify_progress("job_finished", {"total_scraped": len(combined_df)})
        return combined_df

