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
            job = repo.create_job({
                "job_id": job_id,
                "district_name": req.district_name,
                "district_code": req.district_code,
                "start_page": req.start_page,
                "end_page": req.end_page,
                "headless": req.headless,
                "max_workers": req.max_workers,
                "status": "STARTING",
                "started_at": datetime.now(),
            })
            repo.add_log(job_id, "INFO", f"Job registered for {req.district_name} (pages {req.start_page} to {req.end_page})")
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

        # Spawn isolated background process decoupled from Uvicorn reload
        cmd = [
            sys.executable,
            "-m", "app.services.scraper_runner",
            "--job-id", job_id,
            "--district-name", req.district_name,
            "--district-code", req.district_code,
            "--start-page", str(req.start_page),
            "--end-page", str(req.end_page),
            "--max-workers", str(req.max_workers),
        ]
        if req.headless:
            cmd.append("--headless")

        env = os.environ.copy()
        pythonpath = os.pathsep.join([str(_ROOT), str(BACKEND_DIR)])
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = pythonpath

        proc = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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
                for line in iter(proc.stdout.readline, ""):
                    line_str = line.strip()
                    if line_str:
                        self.broadcast(job_id, {
                            "type": "log",
                            "level": "INFO",
                            "message": line_str,
                            "timestamp": datetime.now().isoformat()
                        })
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

