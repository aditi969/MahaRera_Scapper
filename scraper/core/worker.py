"""Multithreaded page and project scraping engine with real-time progress callbacks.

Matches exact workflow, ThreadPoolExecutor, and failure policies
from Cells 6 and 7 of RERA_Scrapping_fixed_v3.ipynb.
"""
import json
import os
import random
import re
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
from scraper.core.building_analyzer import generate_analyzed_building_wise_details
from scraper.core.captcha import CaptchaSolver
from scraper.core.certificate import CertificateExtractor
from scraper.core.checkpoint import CheckpointManager
from scraper.core.config import ScraperConfig
from scraper.core.csv_writer import CsvWriter
from scraper.core.date_utils import compare_last_modified, normalize_date_display, format_date_display
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
        existing_projects_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.config = config or ScraperConfig()
        self.logger = logger or ScraperLogger(log_file=self.config.run_log_file)
        self.on_progress = on_progress
        self.on_record_scraped = on_record_scraped
        self.existing_projects_map = existing_projects_map

        self.browser_manager = BrowserManager(self.config, self.logger)
        self.checkpoint_manager = CheckpointManager(self.config, self.logger)
        self.navigation_manager = NavigationManager(self.config, self.logger, self.browser_manager)
        self.captcha_solver = CaptchaSolver(self.config, self.logger)
        self.cert_extractor = CertificateExtractor(self.config, self.logger)
        self.project_extractor = ProjectExtractor(self.config, self.logger, self.cert_extractor)
        self.csv_writer = CsvWriter(self.config, self.logger)
        self.end_of_results_reached: bool = False
        self.page_all_skipped: bool = False

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
        is_update = task_info.get("is_update", False)
        target_rera_id = task_info.get("rera_id")
        target_name = task_info.get("project_name")

        if cancel_event and cancel_event.is_set():
            return False, None

        if not is_update and self.checkpoint_manager.is_project_already_scraped(checkpoint_data, project_url, target_rera_id):
            self.logger.info(f"⏩ Project {idx + 1} on page {page_number} ({target_rera_id or project_url}) already scraped — skipping.")
            return True, None

        action_desc = "Re-scraping updated" if is_update else "Opening new"
        self.logger.info(f"🚀 {action_desc} project {idx + 1} on page {page_number}: {target_rera_id or project_url}")

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

                from scraper.core.storage import get_temp_file_path
                captcha_img_file = str(get_temp_file_path(f"captcha_p{page_number}_i{idx}_t{threading.get_ident()}.png"))
                captcha_ok = False
                try:
                    captcha_ok = self.captcha_solver.solve_captcha_fully_automated(driver, captcha_img_file)
                finally:
                    if os.path.exists(captcha_img_file):
                        try:
                            os.remove(captcha_img_file)
                        except Exception:
                            pass

                if not captcha_ok:
                    raise Exception("Captcha solve failed after retries")

                df = self.project_extractor.extract_project_data(driver, organization=organization)
                df["Organization"] = organization
                df["Last_Modified"] = last_modified
                df["source_url"] = project_url

                cert_dates = self.cert_extractor.get_cert_dates_with_retries(driver, df=df)
                for _k, _v in cert_dates.items():
                    df[_k] = _v

                rera_id = None
                if "Registration Number" in df.columns and len(df["Registration Number"]) > 0:
                    rera_id = df["Registration Number"].iloc[0]

                if not rera_id and target_rera_id:
                    rera_id = target_rera_id
                    df["Registration Number"] = target_rera_id

                with self.checkpoint_manager.csv_lock:
                    saved_df = self.csv_writer.save_scraped_project_row(
                        df, self.config.output_csv, limit=self.config.excel_char_limit, is_update=is_update
                    )

                if rera_id:
                    self.checkpoint_manager.update_existing_project(
                        rera_id,
                        last_modified=last_modified,
                        project_name=df["Project Name"].iloc[0] if "Project Name" in df.columns else (target_name or ""),
                    )

                self.checkpoint_manager.record_scrape_success(rera_id, is_update=is_update)
                self.checkpoint_manager.mark_project_completed(checkpoint_data, project_url, rera_id=rera_id)

                status_label = "updated" if is_update else "scraped"
                self.logger.info(f"✅ Project {idx + 1} on page {page_number} {status_label} successfully! (RERA ID: {rera_id})")

                # Ingestion callback (updates/inserts in DB)
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
                    "project_name": df["Project Name"].iloc[0] if "Project Name" in df.columns else (target_name or ""),
                    "is_update": is_update,
                    "website_last_modified": last_modified,
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
        self.checkpoint_manager.record_project_status(
            rera_id=target_rera_id or f"UNKNOWN-P{page_number}-I{idx}",
            project_name=target_name or "Unknown Project",
            status="FAILED",
            website_last_modified=last_modified,
            action="Failed",
            details=f"Failed after {self.config.max_project_retries} retries",
        )
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
                if self.navigation_manager.is_last_page_reached:
                    self.end_of_results_reached = True
                    self.logger.info(f"🏁 Page {page_number} is past the last page of results. Concluding scrape cleanly.")
                    return []
                if self.navigation_manager.check_and_dismiss_no_records_popup(driver):
                    self.end_of_results_reached = True
                    self.logger.info(f"🏁 Page {page_number} returned 'No Records Found'. Reached end of available search results.")
                    return []
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
                    self.end_of_results_reached = True
                    if page_number > 1:
                        self.logger.info(f"🏁 Page {page_number} returned 'No Records Found'. Reached end of available search results.")
                    else:
                        self.logger.info(f"ℹ️ Search filters returned 0 matching records on MahaRERA.")
                    return []
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
                    card_text = section.text

                    # 1. Extract RERA ID from card (# P519... or P5...)
                    id_match = re.search(r'#?\s*(P\d{11,})', card_text)
                    card_rera_id = id_match.group(1).strip() if id_match else None
                    if not card_rera_id:
                        try:
                            id_el = section.find_element(By.XPATH, ".//*[contains(text(), 'P5') or contains(text(), '#')]")
                            m = re.search(r'(P\d{11,})', id_el.text)
                            card_rera_id = m.group(1).strip() if m else None
                        except Exception:
                            card_rera_id = None

                    # 2. Extract Project Name from card
                    card_project_name = None
                    try:
                        name_el = section.find_element(
                            By.XPATH,
                            ".//h4 | .//h5 | .//strong | .//b | .//div[contains(@class,'projectName')] | "
                            ".//p[contains(@class,'bold') and not(contains(@class,'darkBlue'))]"
                        )
                        card_project_name = name_el.text.strip()
                    except Exception:
                        pass

                    # 3. Extract Organization / Promoter
                    try:
                        organization = section.find_element(By.XPATH, ".//p[@class='darkBlue bold ']").text.strip()
                    except Exception:
                        organization = None

                    # 4. Extract Last Modified date
                    last_modified = None
                    try:
                        last_modified = section.find_element(
                            By.XPATH,
                            ".//div[@class='greyColor' and contains(text(),'Last Modified')]/following-sibling::p | "
                            ".//*[contains(text(),'Last Modified')]/following-sibling::*"
                        ).text.strip()
                    except Exception:
                        m_date = re.search(r'Last\s*Modified\s*[:\n\r\s]+([0-9]{2,4}[-/][0-9]{1,2}[-/][0-9]{2,4})', card_text, re.IGNORECASE)
                        last_modified = m_date.group(1).strip() if m_date else None

                    # 5. Extract View Details Link
                    view_details_link = section.find_element(By.LINK_TEXT, "View Details")
                    href_value = view_details_link.get_attribute("href")

                    if not card_rera_id and href_value:
                        m_href = re.search(r'project-detail/([A-Za-z0-9]+)', href_value)
                        if m_href:
                            card_rera_id = m_href.group(1).strip()

                    # SMART LAST MODIFIED DATE CHECK
                    existing_info = self.checkpoint_manager.get_existing_project(card_rera_id)
                    is_existing = existing_info is not None
                    existing_last_mod = existing_info.get("last_modified") if existing_info else None
                    if not card_project_name and existing_info:
                        card_project_name = existing_info.get("project_name")

                    decision = "NEW"
                    reason = "New project"
                    is_update = False

                    if is_existing and self.config.smart_date_check:
                        decision, reason = compare_last_modified(existing_last_mod, last_modified)

                    # Format dates for standard display in logs (e.g. DD-MM-YYYY)
                    existing_disp = format_date_display(existing_last_mod) if is_existing else "Not Found"
                    website_disp = format_date_display(last_modified)

                    if decision == "UNCHANGED_SKIPPED":
                        result_text = "Date matches. Skipping project."
                    elif decision == "UPDATED_RESCRAPED":
                        if not existing_last_mod or not last_modified:
                            result_text = "Missing or invalid Last Modified Date. Re-scraping project."
                        else:
                            result_text = "Last Modified Date changed. Re-scraping project."
                    else:
                        result_text = "New project. Proceeding to scrape."

                    # Display standardized logs as strictly required by specification
                    self.logger.info(f"[SMART CHECK] RERA ID: {card_rera_id or 'UNKNOWN'}")
                    self.logger.info(f"[EXISTING DATE] {existing_disp}")
                    self.logger.info(f"[WEBSITE DATE] {website_disp}")
                    self.logger.info(f"[RESULT] {result_text}")

                    if decision == "UNCHANGED_SKIPPED":
                        # Case 1: Existing Project & Date Matches -> SKIP!
                        self.checkpoint_manager.record_project_status(
                            rera_id=card_rera_id or f"UNKNOWN-P{page_number}-I{idx}",
                            project_name=card_project_name or "Unknown Project",
                            status="UNCHANGED_SKIPPED",
                            website_last_modified=last_modified,
                            existing_last_modified=existing_last_mod,
                            action="Skip",
                            details=reason,
                        )
                        self._notify_progress("project_skipped", {
                            "page": page_number,
                            "project_index": idx,
                            "rera_id": card_rera_id,
                            "project_name": card_project_name,
                            "website_last_modified": last_modified,
                            "existing_last_modified": existing_last_mod,
                            "status": "UNCHANGED_SKIPPED",
                            "reason": reason,
                        })
                        continue  # Completely skipped: do not download PDFs or extract details!

                    elif decision == "UPDATED_RESCRAPED":
                        # Case 2: Existing Project & Date Changed / Missing -> RE-SCRAPE & UPDATE!
                        is_update = True
                        self.checkpoint_manager.record_project_status(
                            rera_id=card_rera_id or f"UNKNOWN-P{page_number}-I{idx}",
                            project_name=card_project_name or "Unknown Project",
                            status="UPDATED_RESCRAPED",
                            website_last_modified=last_modified,
                            existing_last_modified=existing_last_mod,
                            action="Re-scrape and Update",
                            details=reason,
                        )
                        self._notify_progress("project_update_detected", {
                            "page": page_number,
                            "project_index": idx,
                            "rera_id": card_rera_id,
                            "project_name": card_project_name,
                            "website_last_modified": last_modified,
                            "existing_last_modified": existing_last_mod,
                            "status": "UPDATED_RESCRAPED",
                            "reason": reason,
                        })

                    else:
                        # Case 3: New Project (RERA ID Not Found in reference data) -> SCRAPE!
                        self.checkpoint_manager.record_project_status(
                            rera_id=card_rera_id or f"UNKNOWN-P{page_number}-I{idx}",
                            project_name=card_project_name or "Unknown Project",
                            status="NEW",
                            website_last_modified=last_modified,
                            existing_last_modified="Not Available",
                            action="Scrape",
                            details="New project found",
                        )
                        self._notify_progress("project_new_detected", {
                            "page": page_number,
                            "project_index": idx,
                            "rera_id": card_rera_id,
                            "project_name": card_project_name,
                            "website_last_modified": last_modified,
                            "status": "NEW",
                        })

                    tasks.append({
                        "page_number": page_number,
                        "project_index": idx,
                        "project_url": href_value,
                        "organization": organization,
                        "last_modified": last_modified,
                        "rera_id": card_rera_id,
                        "project_name": card_project_name,
                        "is_update": is_update,
                    })
                except Exception as e:
                    self.logger.warning(f"Error preparing task for project {idx + 1} on page {page_number}: {e}")

            if sections:
                if not tasks:
                    self.page_all_skipped = True
                    self.logger.info(f"⏩ Page {page_number}: all {len(sections)} projects are up-to-date in database (skipped from re-scraping).")
                return tasks

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
        checkpoint_data["job_start_page"] = page_start
        self.checkpoint_manager.save_checkpoint_data(checkpoint_data)
        start_page = page_start

        # Pre-index existing projects for smart Last Modified Date checks (CSV priority)
        self.checkpoint_manager.load_existing_project_index(db_projects_map=self.existing_projects_map)

        master_driver = self.browser_manager.create_driver(self.config.headless)
        combined_df = pd.DataFrame()
        consecutive_page_failures = 0

        is_scrape_all = bool(self.config.scrape_all_pages or (page_end is None) or (page_end <= 0))
        effective_end_page = page_end if not is_scrape_all else None
        page_scope_desc = "All Available Pages (Auto-detect)" if is_scrape_all else f"Pages {start_page} to {effective_end_page}"

        self.logger.info(f"🚀 Launching scrape job in [{page_scope_desc}] mode for {self.config.district_name or 'All / Custom filters'}.")

        self._notify_progress("job_started", {
            "start_page": start_page,
            "end_page": effective_end_page,
            "scrape_all_pages": is_scrape_all,
            "district": self.config.district_name
        })

        current_page = start_page
        detected_total_pages = None
        max_safety_pages = 2500

        try:
            while True:
                if effective_end_page and current_page > effective_end_page:
                    self.logger.info(f"🏁 Reached end page {effective_end_page}. Scraping finished.")
                    break

                if current_page > max_safety_pages:
                    self.logger.warning(f"Reached safety limit of {max_safety_pages} pages. Stopping run.")
                    break

                if cancel_event and cancel_event.is_set():
                    self.logger.info("🛑 Scrape job cancellation detected.")
                    break

                page = current_page
                completed_pages = checkpoint_data.get("completed_pages", [])
                if page in completed_pages:
                    self.logger.info(f"⏩ Page {page} already completed — skipping.")
                    if effective_end_page and page >= effective_end_page:
                        self.logger.info(f"🏁 Reached requested end page {effective_end_page}. Scraping finished.")
                        break
                    current_page += 1
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

                page_display_total = effective_end_page or (detected_total_pages if detected_total_pages else "?")
                self.logger.info(f"➡️ Starting scraping from page {page} (scope: page {page}/{page_display_total})...")
                self._notify_progress("page_started", {"page": page, "total_pages": effective_end_page or detected_total_pages})

                tasks = self.fetch_page_project_tasks(master_driver, page, checkpoint_data)
                if tasks:
                    self.logger.info(f"✅ Successfully loaded Page {page}. Found {len(tasks)} projects on page {page}.")

                # Auto-detect total pagination info after loading first page
                if page == start_page and detected_total_pages is None:
                    tot_rec, tot_pg = self.navigation_manager.detect_pagination_info(master_driver)
                    if tot_pg:
                        detected_total_pages = tot_pg
                        if is_scrape_all:
                            effective_end_page = tot_pg
                            self.logger.info(f"📊 Auto-detected total pages: {tot_pg} ({tot_rec} projects). Scraping pages {start_page} to {tot_pg}.")
                        elif effective_end_page and effective_end_page > tot_pg:
                            self.logger.info(f"ℹ️ Requested end page {effective_end_page} exceeds available pages ({tot_pg}). Adjusting end page to {tot_pg}.")
                            effective_end_page = tot_pg

                if not tasks:
                    if getattr(self, "page_all_skipped", False):
                        self.logger.info(f"✅ Page {page} complete: all projects are already up-to-date in database.")
                        self.checkpoint_manager.mark_page_completed(checkpoint_data, page)
                        consecutive_page_failures = 0
                        self.page_all_skipped = False
                        if effective_end_page and page >= effective_end_page:
                            self.logger.info(f"🏁 Reached end page {effective_end_page}. Scraping successfully completed.")
                            break
                        current_page += 1
                        continue

                    if self.end_of_results_reached or self.navigation_manager.is_last_page_reached:
                        self.logger.info(f"🏁 End of available results reached at page {page}. Scraping successfully completed.")
                        break

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

                    if effective_end_page and page >= effective_end_page:
                        self.logger.info(f"🏁 Reached requested end page {effective_end_page}. Scraping finished.")
                        break
                    current_page += 1
                    continue

                consecutive_page_failures = 0

                active_tasks = [
                    t for t in tasks
                    if t.get("is_update") or not self.checkpoint_manager.is_project_already_scraped(
                        checkpoint_data, t["project_url"], t.get("rera_id") or t.get("target_rera_id")
                    )
                ]
                skipped_count = len(tasks) - len(active_tasks)
                if skipped_count:
                    self.logger.info(f"⏩ Skipping {skipped_count} already-scraped project(s) on page {page}.")

                if not active_tasks:
                    self.logger.info(f"✅ All projects on page {page} already processed.")
                    self.checkpoint_manager.mark_page_completed(checkpoint_data, page)
                    self._notify_progress("page_completed", {"page": page})
                    if effective_end_page and page >= effective_end_page:
                        self.logger.info(f"🏁 Reached requested end page {effective_end_page}. Scraping finished.")
                        break
                    current_page += 1
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

                # Automatic Refresh & Retry Pass for failed projects on this page
                if still_missing and not (cancel_event and cancel_event.is_set()):
                    self.logger.info(f"🔄 Immediate auto-retry pass: attempting to scrape {len(still_missing)} remaining project(s) on page {page} with refreshed browser session...")
                    self.browser_manager.close_thread_driver()
                    time.sleep(2)
                    for miss_task in still_missing:
                        if cancel_event and cancel_event.is_set():
                            break
                        try:
                            ok, m_df = self.scrape_single_project_task(miss_task, checkpoint_data, cancel_event)
                            if ok and m_df is not None:
                                page_results.append(m_df)
                                combined_df = pd.concat([combined_df, m_df], ignore_index=True)
                        except Exception as m_err:
                            self.logger.warning(f"Retry failed for project {miss_task.get('rera_id')}: {m_err}")

                    still_missing = [
                        t for t in tasks
                        if not self.checkpoint_manager.is_project_already_scraped(checkpoint_data, t["project_url"])
                    ]

                if not still_missing:
                    self.checkpoint_manager.mark_page_completed(checkpoint_data, page)
                    self.logger.info(f"✅ Extracted {len(tasks)} project entries from page {page}. Page {page} completed successfully.")
                    self._notify_progress("page_completed", {"page": page})
                else:
                    self.logger.warning(f"Page {page} has {len(still_missing)} project(s) still unscraped.")
                    if not self.config.skip_failed_projects:
                        self.logger.info("Stopping run as skip_failed_projects is False.")
                        break

                if effective_end_page and page >= effective_end_page:
                    self.logger.info(f"🏁 Reached requested end page {effective_end_page}. Page range completed successfully.")
                    break

                current_page += 1

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

        if self.config.auto_export_excel:
            self.csv_writer.export_and_verify_dataset(
                self.config.output_csv, self.config.output_xlsx, limit=self.config.excel_char_limit
            )

        summary = self.checkpoint_manager.get_summary_stats()
        self.logger.info("=" * 60)
        self.logger.info("  RERA INSIGHT - SCRAPING JOB EXECUTION SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"  Total Projects Discovered:       {summary['total_discovered']}")
        self.logger.info(f"  New Projects Found:              {summary['new_projects_found']}")
        self.logger.info(f"  Existing Projects Checked:       {summary['existing_checked']}")
        self.logger.info(f"  Unchanged Projects Skipped:      {summary['unchanged_skipped']}")
        self.logger.info(f"  Updated Projects Re-scraped:     {summary['updated_rescraped']}")
        self.logger.info(f"  Successfully Scraped Projects:   {summary['successfully_scraped']}")
        self.logger.info(f"  Failed Projects:                 {summary['failed_projects']}")
        self.logger.info(f"  Total Projects Saved or Updated: {summary['total_saved_or_updated']}")
        self.logger.info("=" * 60)

        self._notify_progress("job_finished", {
            "total_scraped": len(combined_df),
            "summary": summary
        })
        return combined_df

