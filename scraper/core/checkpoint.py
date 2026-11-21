"""Checkpoint, failure recovery, and deduplication tracking for MahaRERA scraper.

Matches exact checkpoint logic and data format from Cell 2 of RERA_Scrapping_fixed_v3.ipynb.
"""
import csv
import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
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
        self._existing_projects_index: Dict[str, Dict[str, Any]] = {}
        self._project_statuses: List[Dict[str, Any]] = []
        self._stats = {
            "total_discovered": 0,
            "new_projects_found": 0,
            "existing_checked": 0,
            "unchanged_skipped": 0,
            "updated_rescraped": 0,
            "successfully_scraped": 0,
            "failed_projects": 0,
            "total_saved_or_updated": 0,
        }

    def load_existing_project_index(
        self,
        db_projects_map: Optional[Dict[str, Dict[str, Any]]] = None,
        search_dirs: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Index all known projects and their Last Modified Date from CSV files (primary) and DB (secondary)."""
        with self._csv_ids_cache_lock:
            index: Dict[str, Dict[str, Any]] = {}
            csv_loaded_count = 0
            xlsx_loaded_count = 0

            # 1. Discover existing CSV and Excel files dynamically across configured output locations
            candidate_files = []
            if self.config.output_csv and os.path.exists(self.config.output_csv):
                candidate_files.append(os.path.abspath(self.config.output_csv))
            if self.config.output_xlsx and os.path.exists(self.config.output_xlsx):
                candidate_files.append(os.path.abspath(self.config.output_xlsx))

            # Build search directories
            workspace_dir = os.path.dirname(os.path.abspath(self.config.output_csv)) if self.config.output_csv else os.getcwd()
            outputs_root = os.path.dirname(workspace_dir) if "outputs" in os.path.basename(workspace_dir).lower() else workspace_dir
            cwd = os.getcwd()

            search_folders = [workspace_dir, outputs_root, cwd]
            if getattr(self.config, "output_dir", None):
                search_folders.append(self.config.output_dir)
            if search_dirs:
                search_folders.extend(search_dirs)

            # Additional standard project output locations
            search_folders.extend([
                os.path.join(cwd, "scraper", "outputs"),
                os.path.join(cwd, "backend"),
                os.path.join(cwd, "Outputs"),
                os.path.join(os.path.dirname(cwd), "Outputs"),
                os.path.join(os.path.dirname(cwd), "scarpping", "scraper", "outputs"),
            ])

            # Deduplicate folder list
            seen_dirs = set()
            valid_dirs = []
            for d in search_folders:
                if d and os.path.exists(d):
                    norm = os.path.normpath(os.path.abspath(d))
                    if norm not in seen_dirs:
                        seen_dirs.add(norm)
                        valid_dirs.append(norm)

            for d in valid_dirs:
                try:
                    for root, dirs, files in os.walk(d):
                        # Skip hidden, git, cache, and virtualenv dirs
                        dirs[:] = [
                            sub for sub in dirs
                            if not sub.startswith(".") and sub not in ("node_modules", ".venv", "__pycache__", ".git")
                        ]
                        for fname in files:
                            fl = fname.lower()
                            if fl.startswith("~$") or fl.startswith("."):
                                continue
                            if fl.endswith(".csv") or fl.endswith(".xlsx"):
                                fp = os.path.normpath(os.path.abspath(os.path.join(root, fname)))
                                if fp not in candidate_files:
                                    candidate_files.append(fp)
                except Exception as scan_err:
                    self.logger.debug(f"Scanning directory {d} for CSV/Excel: {scan_err}")

            for file_path in candidate_files:
                if not os.path.exists(file_path):
                    continue
                try:
                    is_xlsx = file_path.lower().endswith(".xlsx")
                    if is_xlsx:
                        df = pd.read_excel(file_path, dtype=str, nrows=50000)
                    else:
                        df = pd.read_csv(file_path, dtype=str, nrows=50000)

                    id_col = None
                    for c in ["Registration Number", "Rera ID", "rera_id", "Registration_Number", "Rera_ID", "registration_number", "rera id", "RERA ID"]:
                        if c in df.columns:
                            id_col = c
                            break
                    if not id_col:
                        continue

                    name_col = next((c for c in ["Project Name", "project_name", "Project_Name"] if c in df.columns), None)
                    mod_col = next((c for c in ["Last_Modified", "Last Modified", "last_modified", "Last Modified Date", "last_modified_date", "last modified"] if c in df.columns), None)
                    agg_col = next((c for c in ["Aggregate area", "aggregate_area", "Aggregate Area", "Aggregate_area", "Aggregate Land Area"] if c in df.columns), None)
                    land_col = next((c for c in ["Land Area for Project Applied for this Registration", "land_area_applied", "Land_Area_Applied"] if c in df.columns), None)

                    file_records_added = 0
                    for _, row in df.iterrows():
                        raw_id = row.get(id_col)
                        if not raw_id or pd.isna(raw_id):
                            continue
                        r_clean = str(raw_id).strip().upper()
                        if not is_reg_start(r_clean) and not (r_clean.startswith("P") and len(r_clean) >= 6):
                            continue

                        p_name = str(row.get(name_col)).strip() if name_col and not pd.isna(row.get(name_col)) else ""
                        l_mod = str(row.get(mod_col)).strip() if mod_col and not pd.isna(row.get(mod_col)) else ""
                        agg_val = str(row.get(agg_col)).strip() if agg_col and not pd.isna(row.get(agg_col)) else ""
                        land_val = str(row.get(land_col)).strip() if land_col and not pd.isna(row.get(land_col)) else ""
                        if agg_val.lower() in ("project status", "nan", "none", "null"):
                            agg_val = ""
                        if land_val.lower() in ("project status", "nan", "none", "null"):
                            land_val = ""

                        if r_clean not in index:
                            index[r_clean] = {
                                "rera_id": r_clean,
                                "project_name": p_name,
                                "last_modified": l_mod,
                                "aggregate_area": agg_val,
                                "land_area_applied": land_val,
                                "source": f"{'xlsx' if is_xlsx else 'csv'}:{os.path.basename(file_path)}",
                            }
                            file_records_added += 1
                        else:
                            # Fill or upgrade missing details if current file has valid info
                            if not index[r_clean].get("last_modified") and l_mod:
                                index[r_clean]["last_modified"] = l_mod
                            if not index[r_clean].get("project_name") and p_name:
                                index[r_clean]["project_name"] = p_name
                            if not index[r_clean].get("aggregate_area") and agg_val:
                                index[r_clean]["aggregate_area"] = agg_val
                            if not index[r_clean].get("land_area_applied") and land_val:
                                index[r_clean]["land_area_applied"] = land_val

                    if is_xlsx:
                        xlsx_loaded_count += file_records_added
                    else:
                        csv_loaded_count += file_records_added
                except Exception as read_err:
                    self.logger.warning(f"Reading project index from {file_path}: {read_err}")

            # 2. Supplement from database for any projects not found in CSV/Excel
            db_added_count = 0
            if db_projects_map:
                for rid, info in db_projects_map.items():
                    r_clean = str(rid).strip().upper()
                    if r_clean:
                        if r_clean not in index:
                            index[r_clean] = {
                                "rera_id": r_clean,
                                "project_name": info.get("project_name") or "",
                                "last_modified": info.get("last_modified") or "",
                                "aggregate_area": info.get("aggregate_area") or "",
                                "land_area_applied": info.get("land_area_applied") or "",
                                "source": "database",
                            }
                            db_added_count += 1
                        else:
                            # Supplement missing database attributes if CSV/Excel lacked last_modified
                            if not index[r_clean].get("last_modified") and info.get("last_modified"):
                                index[r_clean]["last_modified"] = info.get("last_modified")

            self._existing_projects_index = index
            self._csv_ids_cache = set(index.keys())
            self.logger.info(
                f"Loaded {len(index)} total existing project references with Last Modified dates "
                f"({csv_loaded_count} from CSV files, {xlsx_loaded_count} from Excel files, {db_added_count} from database)."
            )
            return index

    def update_existing_project(self, rera_id: str, last_modified: Optional[str] = None, project_name: Optional[str] = None):
        """Immediately update in-memory reference index when a project is re-scraped or extracted."""
        if not rera_id:
            return
        r_clean = str(rera_id).strip().upper()
        with self._csv_ids_cache_lock:
            if r_clean not in self._existing_projects_index:
                self._existing_projects_index[r_clean] = {"rera_id": r_clean}
            if last_modified:
                self._existing_projects_index[r_clean]["last_modified"] = str(last_modified).strip()
            if project_name:
                self._existing_projects_index[r_clean]["project_name"] = str(project_name).strip()
            self._csv_ids_cache.add(r_clean)

    def get_existing_project(self, rera_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not rera_id:
            return None
        return self._existing_projects_index.get(str(rera_id).strip().upper())

    def record_project_status(
        self,
        rera_id: str,
        project_name: str,
        status: str,
        website_last_modified: Optional[str] = None,
        existing_last_modified: Optional[str] = None,
        action: str = "",
        details: Optional[str] = None,
    ):
        """Record status of an individual project for live telemetry and final summary."""
        with self.checkpoint_lock:
            # Update counters
            self._stats["total_discovered"] += 1
            if status == "NEW":
                self._stats["new_projects_found"] += 1
            elif status == "UNCHANGED_SKIPPED":
                self._stats["existing_checked"] += 1
                self._stats["unchanged_skipped"] += 1
            elif status == "UPDATED_RESCRAPED":
                self._stats["existing_checked"] += 1
                self._stats["updated_rescraped"] += 1
            elif status == "FAILED":
                self._stats["failed_projects"] += 1

            record = {
                "rera_id": rera_id,
                "project_name": project_name or "",
                "status": status,
                "website_last_modified": website_last_modified or "Not Available",
                "existing_last_modified": existing_last_modified or "Not Available",
                "action": action,
                "details": details or "",
                "timestamp": str(datetime.now().strftime("%H:%M:%S")),
            }
            # Avoid duplicate logs for same RERA ID
            self._project_statuses = [p for p in self._project_statuses if p["rera_id"] != rera_id]
            self._project_statuses.append(record)

    def record_scrape_success(self, rera_id: str, is_update: bool = False):
        with self.checkpoint_lock:
            self._stats["successfully_scraped"] += 1
            self._stats["total_saved_or_updated"] += 1
            self.add_scraped_id_to_cache(rera_id)

    def get_project_statuses(self) -> List[Dict[str, Any]]:
        with self.checkpoint_lock:
            return list(self._project_statuses)

    def get_summary_stats(self) -> Dict[str, Any]:
        with self.checkpoint_lock:
            return {
                **self._stats,
                "project_records": list(self._project_statuses),
            }

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
            scraped_ids = {str(i).strip().upper() for i in checkpoint_data.get("scraped_ids", [])}

        if project_url and project_url in scraped_urls:
            return True
        if rera_id and str(rera_id).strip().upper() in scraped_ids:
            return True
        if rera_id:
            csv_ids = {str(c).strip().upper() for c in self.load_existing_csv_rera_ids()}
            if str(rera_id).strip().upper() in csv_ids:
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

    def get_failed_pages(
        self,
        completed_pages: Optional[List[int]] = None,
        page_range: Optional[Tuple[int, Optional[int]]] = None
    ) -> List[int]:
        if not os.path.exists(self.config.failed_pages_csv):
            return []
        try:
            with self.csv_lock:
                df = pd.read_csv(self.config.failed_pages_csv)
                if df.empty or "page" not in df.columns:
                    return []
                pages = set(pd.to_numeric(df["page"], errors="coerce").dropna().astype(int).tolist())
                if completed_pages:
                    pages = pages - set(completed_pages)
                if page_range:
                    start_p, end_p = page_range
                    if end_p is not None and end_p > 0:
                        pages = {p for p in pages if start_p <= p <= end_p}
                    else:
                        pages = {p for p in pages if p >= start_p}
                return sorted(pages)
        except Exception:
            return []

    def get_failed_projects(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.config.failed_projects_csv):
            return []
        try:
            with self.csv_lock:
                df = pd.read_csv(self.config.failed_projects_csv)
                if df.empty:
                    return []
                return df.to_dict(orient="records")
        except Exception:
            return []

