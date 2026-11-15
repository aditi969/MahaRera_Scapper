"""Data Quality and Trust API routes."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.project_service import ProjectService

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("")
def get_data_quality(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Calculate and return field completeness, validation accuracy, and certificate extraction metrics."""
    service = ProjectService(db)
    return service.get_data_quality()

