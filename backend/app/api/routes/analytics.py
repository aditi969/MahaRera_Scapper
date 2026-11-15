"""Analytics API routes."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.project_service import ProjectService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Overview KPI metrics calculated strictly from stored database records."""
    service = ProjectService(db)
    return service.get_overview()


@router.get("/districts")
def get_districts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """District-wise project distribution."""
    service = ProjectService(db)
    return service.get_districts()


@router.get("/status")
def get_status_breakdown(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Project status distribution."""
    service = ProjectService(db)
    return service.get_status_breakdown()


@router.get("/project-types")
def get_project_types(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Project type distribution (Residential, Commercial, Plotted, Mixed, etc.)."""
    service = ProjectService(db)
    return service.get_project_types()


@router.get("/registration-trend")
def get_registration_trend(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Monthly project registration trend."""
    service = ProjectService(db)
    return service.get_registration_trend()


@router.get("/completion-trend")
def get_completion_trend(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Yearly project completion trend."""
    service = ProjectService(db)
    return service.get_completion_trend()

