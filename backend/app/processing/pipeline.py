"""Ingestion pipeline: EXTRACT -> CLEAN -> NORMALIZE -> VALIDATE -> DEDUPLICATE -> STORE.

Preserves exact source data and extraction metadata while recording validation flags and data quality checks.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import Project, ScrapeJob, ScrapeLog
from app.processing.validator import validate_project_record


class IngestionPipeline:
    def __init__(self, db: Session):
        self.db = db

    def ingest_project(
        self,
        raw_record: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> Tuple[Project, bool, List[str]]:
        """Ingest a single project record into the database.
        
        Returns:
            (project_instance, is_new_record, validation_errors)
        """
        cleaned, errors, validation_status = validate_project_record(raw_record)
        rera_id = cleaned["rera_id"]

        allowed_cols = {c.name for c in Project.__table__.columns}
        valid_cleaned = {k: v for k, v in cleaned.items() if k in allowed_cols}

        # Deduplication check
        existing = self.db.query(Project).filter(Project.rera_id == rera_id).first()
        is_new = existing is None

        if existing:
            # Update fields while preserving previously available data if new field is missing/empty
            for key, val in valid_cleaned.items():
                if hasattr(existing, key):
                    old_val = getattr(existing, key)
                    # If incoming value is empty/null and old value was present, preserve old value
                    if (val is None or val == "" or val == {} or val == []) and (old_val is not None and old_val != "" and old_val != {} and old_val != []):
                        continue
                    setattr(existing, key, val)
            project = existing
        else:
            project = Project(**valid_cleaned)
            self.db.add(project)

        self.db.flush()
        return project, is_new, errors

    def ingest_batch(
        self,
        records: List[Dict[str, Any]],
        job_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Ingest a list of raw records with transaction management."""
        stats = {
            "total": len(records),
            "inserted": 0,
            "updated": 0,
            "errors": 0,
        }

        try:
            for rec in records:
                try:
                    _, is_new, errs = self.ingest_project(rec, job_id=job_id)
                    if is_new:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                    if errs:
                        stats["errors"] += len(errs)
                except Exception as row_err:
                    self.db.rollback()
                    stats["errors"] += 1
                    continue
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return stats

