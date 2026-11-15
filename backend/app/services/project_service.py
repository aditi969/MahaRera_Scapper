"""Project service: business logic for project listing, details, and analytics."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectListItem, ProjectListResponse, ProjectResponse


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.repo = ProjectRepository(session)

    def list_projects(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        district: Optional[str] = None,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
        sort_by: str = "date_of_registration",
        sort_dir: str = "desc",
    ) -> ProjectListResponse:
        projects, total = self.repo.list_projects(
            page=page,
            page_size=page_size,
            search=search,
            district=district,
            status=status,
            project_type=project_type,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        items = [ProjectListItem.model_validate(p) for p in projects]
        return ProjectListResponse(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_project(self, rera_id: str) -> Optional[ProjectResponse]:
        project = self.repo.get_by_rera_id(rera_id)
        if project is None:
            return None
        return ProjectResponse.model_validate(project)

    def get_locations(
        self,
        district: Optional[str] = None,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        projects = self.repo.get_locations(district=district, status=status, project_type=project_type)
        return [
            {
                "rera_id": p.rera_id,
                "project_name": p.project_name,
                "project_status": p.project_status,
                "district": p.district,
                "project_type": p.project_type,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "promoter_details": p.promoter_details,
            }
            for p in projects
        ]

    def get_overview(self) -> Dict[str, Any]:
        return self.repo.get_overview_kpis()

    def get_districts(self) -> List[Dict[str, Any]]:
        return self.repo.get_district_stats()

    def get_status_breakdown(self) -> List[Dict[str, Any]]:
        return self.repo.get_status_stats()

    def get_project_types(self) -> List[Dict[str, Any]]:
        return self.repo.get_project_type_stats()

    def get_registration_trend(self) -> List[Dict[str, Any]]:
        return self.repo.get_registration_trend()

    def get_completion_trend(self) -> List[Dict[str, Any]]:
        return self.repo.get_completion_trend()

    def get_data_quality(self) -> Dict[str, Any]:
        return self.repo.get_data_quality_metrics()
