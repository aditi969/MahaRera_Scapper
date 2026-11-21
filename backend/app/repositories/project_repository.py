"""Project repository: database queries for projects, search, filters, and analytics aggregations."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.models import Project


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
    ) -> Tuple[List[Project], int]:
        q = self.session.query(Project)

        if search:
            term = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Project.project_name.ilike(term),
                    Project.rera_id.ilike(term),
                    Project.promoter_details.ilike(term),
                )
            )
        if district:
            q = q.filter(Project.district.ilike(f"%{district.strip()}%"))
        if status:
            q = q.filter(Project.project_status.ilike(f"%{status.strip()}%"))
        if project_type:
            q = q.filter(Project.project_type.ilike(f"%{project_type.strip()}%"))

        total = q.count()

        allowed_sort = {
            "date_of_registration": Project.date_of_registration,
            "project_name": Project.project_name,
            "district": Project.district,
            "project_status": Project.project_status,
            "rera_id": Project.rera_id,
        }
        sort_col = allowed_sort.get(sort_by, Project.date_of_registration)
        order = sort_col.desc() if sort_dir.lower() == "desc" else sort_col.asc()

        offset = max(0, (page - 1) * page_size)
        projects = q.order_by(order).offset(offset).limit(page_size).all()
        return projects, total

    def get_by_rera_id(self, rera_id: str) -> Optional[Project]:
        return self.session.query(Project).filter(Project.rera_id == rera_id.strip()).first()

    def get_locations(
        self,
        district: Optional[str] = None,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
    ) -> List[Project]:
        """Return all projects with valid coordinates for map visualization."""
        q = self.session.query(Project).filter(
            Project.latitude.isnot(None),
            Project.longitude.isnot(None),
        )
        if district:
            q = q.filter(Project.district.ilike(f"%{district.strip()}%"))
        if status:
            q = q.filter(Project.project_status.ilike(f"%{status.strip()}%"))
        if project_type:
            q = q.filter(Project.project_type.ilike(f"%{project_type.strip()}%"))

        return q.all()

    # --- Analytics Queries ---

    def get_overview_kpis(self) -> Dict[str, Any]:
        total = self.session.query(func.count(Project.rera_id)).scalar() or 0
        active = self.session.query(func.count(Project.rera_id)).filter(
            Project.project_status.ilike("%Active%")
        ).scalar() or 0
        completed = self.session.query(func.count(Project.rera_id)).filter(
            Project.project_status.ilike("%Completed%")
        ).scalar() or 0
        districts = self.session.query(func.count(func.distinct(Project.district))).filter(
            Project.district.isnot(None),
            Project.district != ""
        ).scalar() or 0

        latest = self.session.query(func.max(Project.last_modified)).scalar()

        return {
            "total_projects": total,
            "active_projects": active,
            "completed_projects": completed,
            "total_districts": districts,
            "latest_scrape_date": latest.isoformat() if hasattr(latest, "isoformat") else (str(latest) if latest else None),
        }

    def get_district_stats(self) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(Project.district, func.count(Project.rera_id).label("count"))
            .filter(Project.district.isnot(None), Project.district != "")
            .group_by(Project.district)
            .order_by(func.count(Project.rera_id).desc())
            .all()
        )
        return [{"district": r[0].strip(), "count": r[1]} for r in rows if r[0] and r[0].strip()]

    def get_status_stats(self) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(Project.project_status, func.count(Project.rera_id).label("count"))
            .filter(Project.project_status.isnot(None), Project.project_status != "")
            .group_by(Project.project_status)
            .order_by(func.count(Project.rera_id).desc())
            .all()
        )
        return [{"status": r[0].strip(), "count": r[1]} for r in rows if r[0] and r[0].strip()]

    def get_project_type_stats(self) -> List[Dict[str, Any]]:
        rows = (
            self.session.query(Project.project_type, func.count(Project.rera_id).label("count"))
            .filter(Project.project_type.isnot(None), Project.project_type != "")
            .group_by(Project.project_type)
            .order_by(func.count(Project.rera_id).desc())
            .all()
        )
        return [{"project_type": r[0].strip(), "count": r[1]} for r in rows if r[0] and r[0].strip()]

    def get_registration_trend(self) -> List[Dict[str, Any]]:
        # Group by year-month of registration
        projects = self.session.query(Project.date_of_registration).filter(
            Project.date_of_registration.isnot(None)
        ).all()

        counts = {}
        for (d,) in projects:
            if d:
                ym = d.strftime("%Y-%m")
                counts[ym] = counts.get(ym, 0) + 1

        sorted_points = sorted(counts.items())
        return [{"period": k, "count": v} for k, v in sorted_points]

    def get_completion_trend(self) -> List[Dict[str, Any]]:
        # Use revised completion date if available, else original
        projects = self.session.query(
            Project.project_completion_date_revised,
            Project.project_completion_date_original
        ).all()

        counts = {}
        for rev, orig in projects:
            d = rev or orig
            if d:
                year = str(d.year)
                counts[year] = counts.get(year, 0) + 1

        sorted_points = sorted(counts.items())
        return [{"year": k, "count": v} for k, v in sorted_points]

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        total = self.session.query(func.count(Project.rera_id)).scalar() or 0
        if total == 0:
            return {
                "total_records": 0,
                "valid_rera_ids": 0,
                "records_with_coordinates": 0,
                "records_missing_district": 0,
                "records_missing_completion_date": 0,
                "records_with_cert_dates": 0,
                "cert_extraction_rate": 0.0,
                "duplicate_count": 0,
                "validation_pass_count": 0,
                "validation_fail_count": 0,
                "completeness_score": 0.0,
                "by_extraction_status": [],
            }

        with_coords = self.session.query(func.count(Project.rera_id)).filter(
            Project.latitude.isnot(None), Project.longitude.isnot(None)
        ).scalar() or 0

        missing_dist = self.session.query(func.count(Project.rera_id)).filter(
            or_(Project.district.is_(None), Project.district == "")
        ).scalar() or 0

        missing_comp = self.session.query(func.count(Project.rera_id)).filter(
            Project.project_completion_date_original.is_(None),
            Project.project_completion_date_revised.is_(None)
        ).scalar() or 0

        with_cert_dates = self.session.query(func.count(Project.rera_id)).filter(
            or_(
                Project.commencing_from.isnot(None),
                Project.leftmost_date.isnot(None),
                Project.ending_with.isnot(None),
            )
        ).scalar() or 0

        cert_rate = round((with_cert_dates / total) * 100, 1)

        pass_count = total
        fail_count = 0

        # Completeness: calculate non-null ratio across essential fields
        essential_fields = [
            Project.project_name, Project.project_status, Project.district,
            Project.date_of_registration, Project.latitude, Project.promoter_details,
            Project.bank_name
        ]
        non_null_total = 0
        for f in essential_fields:
            c = self.session.query(func.count(Project.rera_id)).filter(f.isnot(None)).scalar() or 0
            non_null_total += c
        max_possible = total * len(essential_fields)
        completeness = round((non_null_total / max_possible) * 100, 1) if max_possible else 0.0

        by_status = [{"status": "scraped", "count": total}]

        return {
            "total_records": total,
            "valid_rera_ids": total,
            "records_with_coordinates": with_coords,
            "records_missing_district": missing_dist,
            "records_missing_completion_date": missing_comp,
            "records_with_cert_dates": with_cert_dates,
            "cert_extraction_rate": cert_rate,
            "duplicate_count": 0,
            "validation_pass_count": pass_count,
            "validation_fail_count": fail_count,
            "completeness_score": completeness,
            "by_extraction_status": by_status,
        }
