"""Projects API routes."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.storage import CSV_EXPORTS_DIR, EXCEL_EXPORTS_DIR
from app.database.session import get_db
from app.models.models import Project
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


@router.get("/export/csv")
def export_projects_csv(
    district: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    project_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Export filtered projects from PostgreSQL to a designated CSV file."""
    query = db.query(Project)
    if district:
        query = query.filter(Project.district.ilike(f"%{district.strip()}%"))
    if status:
        query = query.filter(Project.project_status.ilike(f"%{status.strip()}%"))
    if project_type:
        query = query.filter(Project.project_type.ilike(f"%{project_type.strip()}%"))
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            Project.project_name.ilike(s) | Project.rera_id.ilike(s) | Project.promoter_details.ilike(s)
        )

    projects = query.order_by(Project.date_of_registration.desc()).all()
    rows = []
    for p in projects:
        d = {col.name: getattr(p, col.name) for col in Project.__table__.columns}
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                d[k] = json.dumps(v, ensure_ascii=False) if v else ""
        rows.append(d)

    df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"projects_export_{timestamp}.csv"
    CSV_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    export_path = CSV_EXPORTS_DIR / export_filename
    df.to_csv(export_path, index=False, encoding="utf-8-sig")

    return FileResponse(
        path=str(export_path),
        filename=export_filename,
        media_type="text/csv",
    )


@router.get("/export/excel")
def export_projects_excel(
    district: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    project_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Export filtered projects from PostgreSQL to a designated Excel file."""
    query = db.query(Project)
    if district:
        query = query.filter(Project.district.ilike(f"%{district.strip()}%"))
    if status:
        query = query.filter(Project.project_status.ilike(f"%{status.strip()}%"))
    if project_type:
        query = query.filter(Project.project_type.ilike(f"%{project_type.strip()}%"))
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            Project.project_name.ilike(s) | Project.rera_id.ilike(s) | Project.promoter_details.ilike(s)
        )

    projects = query.order_by(Project.date_of_registration.desc()).all()
    rows = []
    for p in projects:
        d = {col.name: getattr(p, col.name) for col in Project.__table__.columns}
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                d[k] = json.dumps(v, ensure_ascii=False)[:32000] if v else ""
            elif isinstance(v, str) and len(v) > 32000:
                d[k] = v[:32000]
        rows.append(d)

    df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"projects_export_{timestamp}.xlsx"
    EXCEL_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXCEL_EXPORTS_DIR / export_filename
    df.to_excel(export_path, index=False, engine="openpyxl")

    return FileResponse(
        path=str(export_path),
        filename=export_filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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

