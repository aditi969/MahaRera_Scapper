"""Dedicated Scraper Runner Process.

Runs in an isolated process decoupled from FastAPI/Uvicorn, ensuring that
API reloads, file watchers, or server restarts do not interrupt active
Selenium browser sessions.
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.database.session import SessionLocal
from app.models.models import ScrapeJob, ScrapeLog
from app.processing.pipeline import IngestionPipeline
from app.repositories.scraper_repository import ScraperRepository
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger
from scraper.core.worker import ScraperWorker


def run_isolated_scraper(
    job_id: str,
    district_name: str,
    district_code: str,
    start_page: int,
    end_page: int,
    max_workers: int,
    headless: bool,
):
    print(f"[RUNNER] Starting isolated scrape process for Job {job_id} (PID: {os.getpid()})")

    # Own database session
    db = SessionLocal()
    repo = ScraperRepository(db)
    pipeline = IngestionPipeline(db)

    # Update job state to RUNNING
    try:
        job = repo.get_job(job_id)
        if job:
            job.status = "RUNNING"
            job.started_at = datetime.now()
            db.commit()
    except Exception as e:
        print(f"[RUNNER] Error updating job to RUNNING: {e}")

    def log_callback(level: str, msg: str):
        try:
            log_db = SessionLocal()
            log_repo = ScraperRepository(log_db)
            log_repo.add_log(job_id, level, msg)
            log_db.commit()
            log_db.close()
        except Exception:
            pass
        print(f"[{level}] {msg}")

    def progress_callback(event: Dict[str, Any]):
        event_type = event.get("type")
        try:
            update_db = SessionLocal()
            job_rec = update_db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
            if job_rec:
                if event_type == "page_started":
                    job_rec.current_page = event.get("page", job_rec.current_page)
                elif event_type == "project_extracted":
                    job_rec.projects_extracted = (job_rec.projects_extracted or 0) + 1
                elif event_type == "project_failed":
                    job_rec.projects_failed = (job_rec.projects_failed or 0) + 1
                update_db.commit()
            update_db.close()
        except Exception as prog_e:
            print(f"[RUNNER] Progress update error: {prog_e}")

    def record_scraped_callback(row_dict: Dict[str, Any]):
        try:
            pipeline.ingest_project(row_dict, job_id=job_id)
            db.commit()
        except Exception as ing_e:
            db.rollback()
            log_callback("WARNING", f"Database incremental upsert error: {ing_e}")

    # Configure scraper with performance bounds
    output_dir = PROJECT_ROOT / "scraper" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = ScraperConfig(
        start_page=start_page,
        end_page=end_page,
        district_name=district_name,
        district_code=district_code,
        max_workers=max_workers,
        headless=headless,
        output_csv=str(output_dir / f"output_{job_id}.csv"),
        output_xlsx=str(output_dir / f"output_{job_id}.xlsx"),
        checkpoint_file=str(output_dir / f"checkpoint_{job_id}.json"),
        run_log_file=str(output_dir / f"run_log_{job_id}.txt"),
    )

    logger = ScraperLogger(log_file=config.run_log_file, callback=log_callback)
    worker = ScraperWorker(
        config=config,
        logger=logger,
        on_progress=progress_callback,
        on_record_scraped=record_scraped_callback,
    )

    try:
        log_callback("INFO", f"Scraper worker initialized. Pages {start_page} to {end_page - 1} for {district_name}")
        df = worker.run_scrape(page_start=start_page, page_end=end_page)

        # Generate PostgreSQL / PL/pgSQL dump file (.sql) alongside CSV and XLSX
        if df is not None and not df.empty:
            try:
                from scraper.core.sql_exporter import generate_postgresql_dump
                sql_file = output_dir / f"output_{job_id}.sql"
                generate_postgresql_dump(df.to_dict(orient="records"), sql_file, job_id=job_id)
                log_callback("INFO", f"PostgreSQL/PL-pgSQL script generated successfully: {sql_file}")
            except Exception as sql_err:
                log_callback("WARNING", f"Could not generate SQL script: {sql_err}")

        # Check final status
        check_db = SessionLocal()
        final_job = check_db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
        if final_job and final_job.status != "CANCELLED":
            if final_job.projects_failed and final_job.projects_failed > 0:
                final_job.status = "COMPLETED_WITH_ERRORS"
            else:
                final_job.status = "COMPLETED"
            final_job.completed_at = datetime.now()
            final_job.projects_extracted = len(df) if df is not None else final_job.projects_extracted
            check_db.commit()

        log_callback("INFO", f"Job finished successfully with {len(df) if df is not None else 0} projects.")
        check_db.close()

    except KeyboardInterrupt:
        log_callback("WARNING", "Job interrupted by user/process termination.")
        try:
            repo.update_job_status(job_id, "CANCELLED", completed_at=datetime.now())
        except Exception:
            pass
    except Exception as exc:
        log_callback("ERROR", f"Job failed with uncaught exception: {exc}")
        try:
            repo.update_job_status(job_id, "FAILED", error_message=str(exc), completed_at=datetime.now())
        except Exception:
            pass
    finally:
        db.close()
        print(f"[RUNNER] Isolated scrape process for Job {job_id} terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Isolated RERA Scraper Runner")
    parser.add_argument("--job-id", required=True, help="Scrape job identifier")
    parser.add_argument("--district-name", default="Raigarh", help="Target district name")
    parser.add_argument("--district-code", default="520", help="Target district code")
    parser.add_argument("--start-page", type=int, default=1, help="Start page")
    parser.add_argument("--end-page", type=int, default=2, help="End page")
    parser.add_argument("--max-workers", type=int, default=1, help="Max browser workers")
    parser.add_argument("--headless", action="store_true", default=True, help="Headless Chrome")

    args = parser.parse_args()

    run_isolated_scraper(
        job_id=args.job_id,
        district_name=args.district_name,
        district_code=args.district_code,
        start_page=args.start_page,
        end_page=args.end_page,
        max_workers=args.max_workers,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()

