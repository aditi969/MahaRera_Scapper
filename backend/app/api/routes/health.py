"""System and CAPTCHA Health Check API Routes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Project
from app.services.captcha_health_service import (
    check_captcha_health,
    get_captcha_operational_metrics,
    run_synthetic_ocr_test,
    find_tesseract_path,
)

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("")
def general_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """System-wide health check covering API, database, and CAPTCHA engine."""
    total_projects = db.query(Project).count()
    captcha_health = check_captcha_health(db, run_self_test=False)

    return {
        "status": "healthy" if captcha_health["status"] != "unhealthy" else "degraded",
        "app_name": "RERA Insight",
        "version": "1.0.0",
        "database": "connected",
        "total_projects": total_projects,
        "captcha": {
            "status": captcha_health["status"],
            "status_label": captcha_health["status_label"],
            "tesseract_version": captcha_health["engine"]["tesseract"]["version"],
            "opencv_version": captcha_health["engine"]["opencv"]["version"],
            "solve_rate_percent": captcha_health["metrics"]["solve_rate_percent"],
            "total_attempts": captcha_health["metrics"]["total_attempts"],
            "total_accepted": captcha_health["metrics"]["total_accepted"],
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/captcha")
def captcha_health(
    run_test: bool = Query(True, description="Execute synthetic OCR self-test"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Detailed health check for CAPTCHA solver engine and OCR pipeline."""
    return check_captcha_health(db, run_self_test=run_test)


@router.get("/captcha/metrics")
def captcha_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """CAPTCHA operational metrics (attempts, solves, failures, success rate)."""
    return get_captcha_operational_metrics(db)


@router.post("/captcha/test")
def test_captcha_ocr() -> Dict[str, Any]:
    """Force an on-demand synthetic OCR test to measure recognition latency and accuracy."""
    tess_path = find_tesseract_path()
    return run_synthetic_ocr_test(tess_path)
