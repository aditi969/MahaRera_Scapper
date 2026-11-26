"""Scraper service: manages scraper jobs, background execution, cancellation, and WebSocket broadcasts."""
from __future__ import annotations

import asyncio
import os
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from app.database.session import SessionLocal
from app.models.models import ScrapeJob, ScrapeLog
from app.processing.pipeline import IngestionPipeline
from app.repositories.scraper_repository import ScraperRepository
from app.schemas.scraper import StartJobRequest

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class ScraperService:
    _instance: Optional["ScraperService"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.ws_subscribers: Dict[str, Set[Callable[[Dict[str, Any]], None]]] = {}

    @classmethod
    def get_instance(cls) -> "ScraperService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, job_id: str, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if job_id not in self.ws_subscribers:
                self.ws_subscribers[job_id] = set()
            self.ws_subscribers[job_id].add(callback)

    def unsubscribe(self, job_id: str, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if job_id in self.ws_subscribers:
                self.ws_subscribers[job_id].discard(callback)

    def broadcast(self, job_id: str, message: Dict[str, Any]):
        with self._lock:
            subscribers = list(self.ws_subscribers.get(job_id, []))
        for cb in subscribers:
            try:
                cb(message)
            except Exception:
                pass

    def start_job(self, req: StartJobRequest) -> Dict[str, Any]:
        """Create and commit a new scrape job in DB, then spawn the isolated worker process."""
        # Prevent starting duplicate concurrent jobs
        with self._lock:
            db_check = SessionLocal()
            try:
                active = db_check.query(ScrapeJob).filter(
                    ScrapeJob.status.in_(["STARTING", "RUNNING"])
                ).first()
                if active:
                    raise ValueError(f"Job '{active.job_id}' is already {active.status}. Please wait or cancel it before starting another.")
            finally:
                db_check.close()

        job_id = f"job-{uuid.uuid4().hex[:8]}"

        db = SessionLocal()
        try:
            repo = ScraperRepository(db)
            target_dist = req.district_name if req.district_name and req.district_name != "All / Any District" else ""
            target_code = req.district_code if req.district_code and target_dist else ""
            if not target_code and target_dist:
                from scraper.core.navigation import MAHARASHTRA_DISTRICT_CODE_MAP
                target_code = MAHARASHTRA_DISTRICT_CODE_MAP.get(target_dist.strip().lower(), "")

            filters_payload = {
                "district_name": target_dist,
                "district_code": target_code,
                "project_type_category": req.project_type_category or "Registered Projects",
                "search_query": req.search_query or "",
                "pincode": req.pincode or "",
                "completion_date": req.completion_date or "",
                "state": req.state or "MAHARASHTRA",
                "division": req.division or "",
                "taluka": req.taluka or "",
                "village": req.village or "",
                "smart_date_check": req.smart_date_check,
                "scrape_all_pages": req.scrape_all_pages,
            }
            display_dist = target_dist or (f"Query: {req.search_query}" if req.search_query else (f"Pin: {req.pincode}" if req.pincode else "All Districts"))
            page_scope_log = "all available pages" if req.scrape_all_pages else f"pages {req.start_page} to {req.end_page}"
            job = repo.create_job({
                "job_id": job_id,
                "district_name": display_dist,
                "district_code": target_code,
                "start_page": req.start_page,
                "end_page": None if req.scrape_all_pages else req.end_page,
                "headless": req.headless,
                "max_workers": req.max_workers,
                "status": "STARTING",
                "filters_json": filters_payload,
                "started_at": datetime.now(),
            })
            filter_desc = f"query='{req.search_query}' " if req.search_query else ""
            if req.pincode:
                filter_desc += f"pin='{req.pincode}' "
            repo.add_log(job_id, "INFO", f"Job registered for {display_dist} ({page_scope_log}) {filter_desc}".strip())
            db.commit()

            # Construct clean response dictionary while session is active (prevents DetachedInstanceError)
            job_dto = {
                "job_id": job.job_id,
                "district_name": job.district_name,
                "district_code": job.district_code,
                "start_page": job.start_page,
                "end_page": job.end_page,
                "headless": job.headless,
                "max_workers": job.max_workers,
                "status": job.status,
                "projects_found": job.projects_found or 0,
                "projects_extracted": job.projects_extracted or 0,
                "projects_failed": job.projects_failed or 0,
                "current_page": job.current_page or req.start_page,
                "certificates_extracted": job.certificates_extracted or 0,
                "certificates_failed": job.certificates_failed or 0,
                "filters_json": job.filters_json,
                "summary_json": job.summary_json,
                "error_message": job.error_message,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        # Resolve dedicated virtual environment python and isolated runner script
        venv_python = _ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable
        runner_script = Path(__file__).resolve().parent / "scraper_runner.py"

        # Spawn isolated background process decoupled from Uvicorn reload
        cmd = [
            python_exe,
            str(runner_script),
            "--job-id", str(job_id),
            "--start-page", str(req.start_page),
            "--max-workers", str(req.max_workers),
        ]
        if req.scrape_all_pages:
            cmd.append("--scrape-all-pages")
        elif req.end_page:
            cmd.extend(["--end-page", str(req.end_page)])
        if target_dist:
            cmd.extend(["--district-name", str(target_dist)])
        if target_code:
            cmd.extend(["--district-code", str(target_code)])
        if req.project_type_category:
            cmd.extend(["--project-type-category", str(req.project_type_category)])
        if req.search_query:
            cmd.extend(["--search-query", str(req.search_query)])
        if req.pincode:
            cmd.extend(["--pincode", str(req.pincode)])
        if req.completion_date:
            cmd.extend(["--completion-date", str(req.completion_date)])
        if req.state:
            cmd.extend(["--state", str(req.state)])
        if req.division:
            cmd.extend(["--division", str(req.division)])
        if req.taluka:
            cmd.extend(["--taluka", str(req.taluka)])
        if req.village:
            cmd.extend(["--village", str(req.village)])
        if req.headless:
            cmd.append("--headless")
        if req.smart_date_check:
            cmd.append("--smart-date-check")

        env = os.environ.copy()
        pythonpath = os.pathsep.join([str(_ROOT), str(BACKEND_DIR)])
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = pythonpath
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        proc = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        with self._lock:
            self.active_processes[job_id] = proc

        # Stream process output to WebSocket subscribers in a dedicated reader thread
        stream_thread = threading.Thread(
            target=self._stream_process_output,
            args=(job_id, proc),
            daemon=True,
            name=f"StreamWorker-{job_id}"
        )
        stream_thread.start()

        return job_dto

    def _stream_process_output(self, job_id: str, proc: subprocess.Popen):
        try:
            if proc.stdout:
                import json
                for line in iter(proc.stdout.readline, ""):
                    line_str = line.strip()
                    if line_str:
                        # Intercept live scraped project record for real-time frontend streaming
                        if line_str.startswith("__PROJECT_SCRAPED__:"):
                            try:
                                json_part = line_str.split("__PROJECT_SCRAPED__:", 1)[1]
                                proj_obj = json.loads(json_part)
                                self.broadcast(job_id, {
                                    "type": "project_scraped",
                                    "project": proj_obj,
                                    "timestamp": datetime.now().isoformat()
                                })
                            except Exception:
                                pass
                            continue

                        # Intercept live stats synchronization for real-time dashboard cards
                        if line_str.startswith("__JOB_STATS__:"):
                            try:
                                json_part = line_str.split("__JOB_STATS__:", 1)[1]
                                stats_obj = json.loads(json_part)
                                self.broadcast(job_id, {
                                    "type": "job_stats",
                                    "summary": stats_obj,
                                    "timestamp": datetime.now().isoformat()
                                })
                            except Exception:
                                pass
                            continue

                        # Filter out internal ChromeDriver C++ binary addresses (e.g. "(No symbol) [0x7ff...]")
                        if line_str.startswith("(No symbol) [") or line_str == "Stacktrace:" or line_str.startswith("GetHandleVerifier [0x"):
                            continue

                        level = "INFO"
                        if "ERROR" in line_str or "Traceback" in line_str or "Exception" in line_str or "Error:" in line_str or "failed" in line_str.lower():
                            level = "ERROR"
                        elif "WARNING" in line_str:
                            level = "WARNING"

                        self.broadcast(job_id, {
                            "type": "log",
                            "level": level,
                            "message": line_str,
                            "timestamp": datetime.now().isoformat()
                        })

                        # Always persist process output logs into DB so user can see them in UI
                        try:
                            log_db = SessionLocal()
                            log_repo = ScraperRepository(log_db)
                            log_repo.add_log(job_id, level, line_str[:1000])
                            log_db.commit()
                            log_db.close()
                        except Exception:
                            pass
            proc.wait()
        except Exception:
            pass
        finally:
            with self._lock:
                self.active_processes.pop(job_id, None)

            # Check final job state from database and notify subscribers
            db = SessionLocal()
            try:
                repo = ScraperRepository(db)
                job = repo.get_job(job_id)
                if job:
                    if proc.returncode != 0 and job.status in ("STARTING", "RUNNING"):
                        repo.update_job_status(job_id, "FAILED", error_message=f"Process exited prematurely with code {proc.returncode}")
                        repo.add_log(job_id, "ERROR", f"Worker process exited prematurely (exit code {proc.returncode})")
                        db.commit()
                        job = repo.get_job(job_id)

                    self.broadcast(job_id, {
                        "type": "complete",
                        "status": job.status,
                        "projects_extracted": job.projects_extracted,
                        "projects_failed": job.projects_failed,
                        "summary": job.summary_json,
                    })
            finally:
                db.close()

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            proc = self.active_processes.get(job_id)

        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

        db = SessionLocal()
        try:
            repo = ScraperRepository(db)
            repo.update_job_status(job_id, "CANCELLED", completed_at=datetime.now())
            repo.add_log(job_id, "WARNING", "Job cancellation requested by user.")
        finally:
            db.close()

        self.broadcast(job_id, {"type": "status", "status": "CANCELLED", "message": "Job cancelled"})
        return True

    def retry_job(self, job_id: str) -> Dict[str, Any]:
        """Restart or retry scraping for a previous job, picking up from checkpoints to retry failed projects/pages."""
        db = SessionLocal()
        try:
            repo = ScraperRepository(db)
            old_job = repo.get_job(job_id)
            if not old_job:
                raise ValueError(f"Job '{job_id}' not found.")
            filters = old_job.filters_json or {}
            start_req = StartJobRequest(
                district_name=filters.get("district_name") or (old_job.district_name if old_job.district_name and not old_job.district_name.startswith("All") else None),
                district_code=filters.get("district_code") or old_job.district_code,
                start_page=old_job.start_page or 1,
                end_page=old_job.end_page or 2,
                max_workers=old_job.max_workers or 1,
                headless=old_job.headless if old_job.headless is not None else True,
                project_type_category=filters.get("project_type_category", "Registered Projects"),
                search_query=filters.get("search_query", ""),
                pincode=filters.get("pincode", ""),
                completion_date=filters.get("completion_date", ""),
                state=filters.get("state", "MAHARASHTRA"),
                division=filters.get("division", ""),
                taluka=filters.get("taluka", ""),
                village=filters.get("village", ""),
                smart_date_check=filters.get("smart_date_check", True),
                scrape_all_pages=filters.get("scrape_all_pages", False),
            )
        finally:
            db.close()
        return self.start_job(start_req)

