"""Projects API routes."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.project import ProjectListResponse, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Search project name, RERA ID, or promoter"),
    district: Optional[str] = Query(default=None, description="Filter by district"),
    status: Optional[str] = Query(default=None, description="Filter by status (e.g. Active, Completed)"),
    project_type: Optional[str] = Query(default=None, description="Filter by project type"),
    sort_by: str = Query(default="date_of_registration", description="Sort field"),
    sort_dir: str = Query(default="desc", regex="^(asc|desc)$", description="Sort direction"),
    db: Session = Depends(get_db),
):
    """List MahaRERA projects with filtering, full-text search, and pagination."""
    service = ProjectService(db)
    return service.list_projects(
        page=page,
        page_size=page_size,
        search=search,
        district=district,
        status=status,
        project_type=project_type,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/locations")
def get_project_locations(
    district: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    project_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Retrieve only projects that have valid geographic coordinates for interactive map plotting."""
    service = ProjectService(db)
    return service.get_locations(district=district, status=status, project_type=project_type)


@router.get("/{rera_id}", response_model=ProjectResponse)
def get_project(rera_id: str, db: Session = Depends(get_db)):
    """Retrieve comprehensive project profile by RERA registration ID."""
    service = ProjectService(db)
    project = service.get_project(rera_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with RERA ID '{rera_id}' was not found in the database."
        )
    return project

