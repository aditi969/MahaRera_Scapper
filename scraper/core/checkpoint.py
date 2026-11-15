"""Checkpoint, failure recovery, and deduplication tracking for MahaRERA scraper.

Matches exact checkpoint logic and data format from Cell 2 of RERA_Scrapping_fixed_v3.ipynb.
"""
import csv
import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import pandas as pd

from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


def is_reg_start(val: Any) -> bool:
    v = str(val).strip().strip("'\"")
    return v.startswith('P') and len(v) >= 11 and v[1:12].isdigit()


class CheckpointManager:
    def __init__(self, config: ScraperConfig, logger: ScraperLogger):
        self.config = config
        self.logger = logger
        self.checkpoint_lock = threading.Lock()
        self.csv_lock = threading.Lock()
        self._csv_ids_cache: Optional[Set[str]] = None
        self._csv_ids_cache_lock = threading.Lock()

    def load_existing_csv_rera_ids(self, force_reload: bool = False) -> Set[str]:
        with self._csv_ids_cache_lock:
            if self._csv_ids_cache is not None and not force_reload:
                return set(self._csv_ids_cache)

            scraped_ids: Set[str] = set()
            if os.path.exists(self.config.output_csv):
                try:
                    df = pd.read_csv(self.config.output_csv, usecols=["Registration Number"], dtype=str)
                    scraped_ids = set(df["Registration Number"].dropna().astype(str).str.strip().tolist())
                except Exception:
                    try:
                        df = pd.read_csv(self.config.output_csv, usecols=["Rera ID"], dtype=str)
                        scraped_ids = set(df["Rera ID"].dropna().astype(str).str.strip().tolist())
                    except Exception:
                        try:
                            with open(self.config.output_csv, "r", encoding="utf-8", errors="replace") as f:
                                reader = csv.reader(f)
                                for row in reader:
                                    if row and is_reg_start(row[0]):
                                        scraped_ids.add(row[0].strip())
                        except Exception as e:
                            self.logger.warning(f"Reading existing RERA IDs from CSV: {e}")

            self._csv_ids_cache = scraped_ids
            return set(self._csv_ids_cache)

    def add_scraped_id_to_cache(self, rera_id: Optional[str]):
        if not rera_id:
            return
        with self._csv_ids_cache_lock:
            if self._csv_ids_cache is None:
                self._csv_ids_cache = set()
            self._csv_ids_cache.add(str(rera_id).strip())

    def load_checkpoint(self) -> Dict[str, Any]:
        default_data = {
            "scraped_projects": [],
            "scraped_ids": [],
            "completed_pages": [],
            "last_interrupted": None,
            "job_start_page": self.config.start_page
        }

        with self.checkpoint_lock:
            if os.path.exists(self.config.checkpoint_file):
                try:
                    with open(self.config.checkpoint_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    completed = sorted(set(data.get("completed_pages", [])))
                    data["completed_pages"] = completed
                    inferred_floor = completed[0] if completed else self.config.start_page
                    stored_floor = data.get("job_start_page", inferred_floor)
                    data["job_start_page"] = min(stored_floor, inferred_floor, self.config.start_page)

                    self.logger.info(
                        f"Granular checkpoint loaded ({len(data.get('scraped_projects', []))} scraped projects, "
                        f"{len(completed)} completed pages, job_start_page={data['job_start_page']})."
                    )
                    return data
                except Exception as e:
                    self.logger.warning(f"Could not read checkpoint file ({e}), starting clean checkpoint.")

        csv_ids = self.load_existing_csv_rera_ids()
        if csv_ids:
            default_data["scraped_ids"] = list(csv_ids)
            self.logger.info(f"Loaded {len(csv_ids)} already scraped RERA IDs from {self.config.output_csv}.")

        return default_data

    def save_checkpoint_data(self, checkpoint_data: Dict[str, Any]):
        with self.checkpoint_lock:
            try:
                if "completed_pages" in checkpoint_data:
                    checkpoint_data["completed_pages"] = sorted(set(checkpoint_data["completed_pages"]))
                with open(self.config.checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2)
            except Exception as e:
                self.logger.error(f"Error saving checkpoint file: {e}")

    def is_project_already_scraped(self, checkpoint_data: Dict[str, Any], project_url: Optional[str], rera_id: Optional[str] = None) -> bool:
        with self.checkpoint_lock:
            scraped_urls = set(checkpoint_data.get("scraped_projects", []))
            scraped_ids = set(checkpoint_data.get("scraped_ids", []))

        if project_url and project_url in scraped_urls:
            return True
        if rera_id and str(rera_id).strip() in scraped_ids:
            return True
        if rera_id:
            csv_ids = self.load_existing_csv_rera_ids()
            if str(rera_id).strip() in csv_ids:
                return True
        return False

    def mark_project_completed(self, checkpoint_data: Dict[str, Any], project_url: Optional[str], rera_id: Optional[str] = None):
        with self.checkpoint_lock:
            if project_url and project_url not in checkpoint_data["scraped_projects"]:
                checkpoint_data["scraped_projects"].append(project_url)
            if rera_id and str(rera_id).strip() not in checkpoint_data["scraped_ids"]:
                checkpoint_data["scraped_ids"].append(str(rera_id).strip())
            if checkpoint_data.get("last_interrupted"):
                if checkpoint_data["last_interrupted"].get("project_url") == project_url:
                    checkpoint_data["last_interrupted"] = None
        self.save_checkpoint_data(checkpoint_data)

    def record_interrupted_project(self, checkpoint_data: Dict[str, Any], page: int, project_index: int, project_url: str, reason: str = "in_progress"):
        with self.checkpoint_lock:
            checkpoint_data["last_interrupted"] = {
                "page": page,
                "project_index": project_index,
                "project_url": project_url,
                "reason": reason,
                "updated_at": str(datetime.now())
            }
        self.save_checkpoint_data(checkpoint_data)

    def mark_page_completed(self, checkpoint_data: Dict[str, Any], page: int):
        with self.checkpoint_lock:
            if page not in checkpoint_data["completed_pages"]:
                checkpoint_data["completed_pages"].append(page)
                checkpoint_data["completed_pages"].sort()
        self.save_checkpoint_data(checkpoint_data)

    def log_failed_page(self, page: int, reason: str):
        row = pd.DataFrame([{"page": page, "reason": reason, "time": str(datetime.now())}])
        with self.csv_lock:
            row.to_csv(self.config.failed_pages_csv, index=False, mode="a",
                       header=not os.path.exists(self.config.failed_pages_csv))

    def log_failed_project(self, page: int, project_index: int, project_url: str, reason: str):
        row = pd.DataFrame([{"page": page, "project_index": project_index,
                              "project_url": project_url, "reason": reason, "time": str(datetime.now())}])
        with self.csv_lock:
            row.to_csv(self.config.failed_projects_csv, index=False, mode="a",
                       header=not os.path.exists(self.config.failed_projects_csv))

    def get_failed_pages(self) -> List[int]:
        if not os.path.exists(self.config.failed_pages_csv):
            return []
        try:
            with self.csv_lock:
                df = pd.read_csv(self.config.failed_pages_csv)
                return sorted(set(df["page"].tolist()))
        except Exception:
            return []

