"""Scraper repository: CRUD queries for ScrapeJob and ScrapeLog."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import ScrapeJob, ScrapeLog


class ScraperRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_job(self, job_data: Dict[str, Any]) -> ScrapeJob:
        job = ScrapeJob(**job_data)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> Optional[ScrapeJob]:
        return self.session.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()

    def list_jobs(self) -> List[ScrapeJob]:
        return self.session.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).all()

    def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> Optional[ScrapeJob]:
        job = self.get_job(job_id)
        if not job:
            return None
        job.status = status
        for k, v in kwargs.items():
            if hasattr(job, k):
                setattr(job, k, v)
        job.updated_at = datetime.now()
        self.session.commit()
        self.session.refresh(job)
        return job

    def add_log(
        self,
        job_id: str,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ScrapeLog:
        log = ScrapeLog(job_id=job_id, level=level, message=message, extra=extra)
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def get_logs(self, job_id: str, limit: int = 200) -> List[ScrapeLog]:
        return (
            self.session.query(ScrapeLog)
            .filter(ScrapeLog.job_id == job_id)
            .order_by(ScrapeLog.created_at.asc())
            .limit(limit)
            .all()
        )
