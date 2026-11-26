"""Scraper job management API routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import re
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.storage import CSV_PROCESSED_DIR, EXCEL_PROCESSED_DIR
from app.database.session import get_db
from app.repositories.scraper_repository import ScraperRepository
from app.schemas.scraper import (
    JobScrapedDataResponse,
    ScrapedProjectItem,
    ScrapeJobResponse,
    ScrapeLogResponse,
    ScrapePreviewRequest,
    ScrapePreviewResponse,
    StartJobRequest,
)
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scraper", tags=["Scraper Control"])


@router.post("/preview", response_model=ScrapePreviewResponse)
def preview_scraping_job(req: ScrapePreviewRequest, db: Session = Depends(get_db)):
    """Preview matching projects already present in local database based on selected filters."""
    from app.models.models import Project

    query = db.query(Project)

    if req.search_query:
        sq = f"%{req.search_query.strip()}%"
        query = query.filter(
            (Project.rera_id.ilike(sq)) | (Project.project_name.ilike(sq))
        )
    if req.district_name and req.district_name.lower() not in ("all", "select district", ""):
        query = query.filter(Project.district.ilike(f"%{req.district_name.strip()}%"))
    if req.pincode:
        query = query.filter(Project.pin_code.ilike(f"%{req.pincode.strip()}%"))

    total_matching = query.count()
    matching_projects = query.order_by(Project.last_modified.desc()).limit(20).all()

    existing_list = []
    for p in matching_projects:
        existing_list.append({
            "rera_id": p.rera_id,
            "project_name": p.project_name,
            "district": p.district,
            "pincode": p.pin_code,
            "last_modified": p.last_modified,
            "proposed_completion_date": str(p.project_completion_date_revised or p.project_completion_date_original or ""),
            "status": "EXISTING_IN_DB",
        })

    return ScrapePreviewResponse(
        matching_in_database=total_matching,
        existing_projects=existing_list,
        sample_records=existing_list[:5],
        filters_applied={
            "district_name": req.district_name,
            "search_query": req.search_query,
            "pincode": req.pincode,
            "completion_date": req.completion_date,
            "project_type_category": req.project_type_category,
        },
    )


@router.post("/start", response_model=ScrapeJobResponse, status_code=status.HTTP_201_CREATED)
def start_scraping_job(req: StartJobRequest):
    """Launch an asynchronous scraping job with isolated state persistence."""
    service = ScraperService.get_instance()
    try:
        job_dto = service.start_job(req)
        return job_dto
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(ve)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize scrape job: {err}"
        )


@router.get("/jobs", response_model=List[ScrapeJobResponse])
def list_scraping_jobs(db: Session = Depends(get_db)):
    """List all past and active scraping jobs."""
    repo = ScraperRepository(db)
    return repo.list_jobs()


@router.delete("/jobs", status_code=status.HTTP_200_OK)
def clear_scraping_job_history(db: Session = Depends(get_db)):
    """Clear all past scraping job history from the database."""
    repo = ScraperRepository(db)
    cleared_count = repo.clear_all_jobs(include_running=False)
    return {"message": f"Successfully cleared {cleared_count} scraping jobs from history.", "cleared_count": cleared_count}


@router.delete("/jobs/{job_id}", status_code=status.HTTP_200_OK)
def delete_single_scraping_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a single scraping job record and its logs."""
    repo = ScraperRepository(db)
    success = repo.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job '{job_id}' not found."
        )
    return {"message": f"Job '{job_id}' deleted successfully.", "job_id": job_id}


@router.get("/jobs/{job_id}", response_model=ScrapeJobResponse)
def get_scraping_job(job_id: str, db: Session = Depends(get_db)):
    """Get metadata and current status for a specific scraping job."""
    repo = ScraperRepository(db)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job '{job_id}' not found."
        )
    return job


@router.get("/logs/{job_id}", response_model=List[ScrapeLogResponse])
def get_job_logs(job_id: str, db: Session = Depends(get_db)):
    """Retrieve operational execution logs for a job."""
    repo = ScraperRepository(db)
    return repo.get_logs(job_id)


@router.post("/cancel/{job_id}")
def cancel_scraping_job(job_id: str):
    """Request graceful cancellation of a running scraping job."""
    service = ScraperService.get_instance()
    success = service.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not currently running or cannot be cancelled."
        )
    return {"message": f"Cancellation requested for job '{job_id}'", "status": "CANCELLED"}


@router.post("/retry/{job_id}", response_model=ScrapeJobResponse, status_code=status.HTTP_201_CREATED)
def retry_scraping_job(job_id: str):
    """Retry failed projects or pages of a previous job."""
    service = ScraperService.get_instance()
    try:
        new_job_dto = service.retry_job(job_id)
        return new_job_dto
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry scrape job: {err}"
        )


@router.get("/jobs/{job_id}/projects", response_model=JobScrapedDataResponse)
def get_job_scraped_projects(job_id: str, db: Session = Depends(get_db)):
    """Retrieve full project details and extraction decisions for a scraping job."""
    from app.models.models import Project, ScrapeJob

    job = db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scrape job '{job_id}' not found."
        )

    summary = job.summary_json or {}
    project_records = summary.get("project_records") or []
    if not project_records and isinstance(summary.get("project_details"), dict):
        project_records = list(summary["project_details"].values())

    # Also inspect checkpoint file on disk if summary was empty
    if not project_records:
        from app.core.storage import TEMP_DIR
        import json as _json
        chk_file = TEMP_DIR / f"checkpoint_{job_id}.json"
        if chk_file.exists():
            try:
                with open(chk_file, "r", encoding="utf-8") as f:
                    chk_data = _json.load(f)
                    if chk_data.get("scraped_projects"):
                        for sp in chk_data["scraped_projects"]:
                            project_records.append({
                                "rera_id": sp.get("rera_id") or sp.get("Registration Number"),
                                "project_name": sp.get("project_name") or sp.get("Project Name"),
                                "status": "SCRAPED_OK",
                                "action": "Scraped",
                            })
            except Exception:
                pass

    # Build decision lookup by rera_id
    decisions_by_id: Dict[str, Dict[str, Any]] = {}
    for pr in project_records:
        rid = str(pr.get("rera_id") or "").strip().upper()
        if rid:
            decisions_by_id[rid] = pr

    # Find project rows from PostgreSQL DB
    rera_ids = list(decisions_by_id.keys())
    db_projects: List[Project] = []
    if rera_ids:
        db_projects = db.query(Project).filter(Project.rera_id.in_(rera_ids)).all()

    # Only fallback to district for completed legacy jobs where summary wasn't stored
    if not db_projects and not decisions_by_id and job.status == "COMPLETED" and (job.projects_extracted or 0) > 0 and job.district_name and job.district_name.lower() not in ("all", "all / any district", ""):
        db_projects = db.query(Project).filter(Project.district.ilike(f"%{job.district_name.strip()}%")).limit(job.projects_extracted or 100).all()

    # Map db_projects by rera_id
    db_map = {p.rera_id.strip().upper(): p for p in db_projects if p.rera_id}

    items: List[ScrapedProjectItem] = []
    processed_ids = set()

    for rid, dec in decisions_by_id.items():
        processed_ids.add(rid)
        p = db_map.get(rid)
        raw = None
        if p:
            raw = {
                "rera_id": p.rera_id,
                "project_name": p.project_name,
                "project_status": p.project_status,
                "project_type": p.project_type,
                "district": p.district,
                "taluka": p.taluka,
                "locality": p.locality,
                "village": p.village,
                "state_ut": p.state_ut,
                "pin_code": p.pin_code,
                "promoter_details": p.promoter_details,
                "total_land_area": p.total_land_area,
                "aggregate_area": p.aggregate_area,
                "permissible_builtup_area": p.permissible_builtup_area,
                "sanctioned_builtup_area": p.sanctioned_builtup_area,
                "project_completion_date_original": str(p.project_completion_date_original or ""),
                "project_completion_date_revised": str(p.project_completion_date_revised or ""),
                "boundaries_east": p.boundaries_east,
                "boundaries_west": p.boundaries_west,
                "boundaries_north": p.boundaries_north,
                "boundaries_south": p.boundaries_south,
                "bank_name": p.bank_name,
                "ifsc_code": p.ifsc_code,
                "bank_address": p.bank_address,
                "bhk_details": p.bhk_details,
                "building_details": p.building_details,
                "summary_of_apartments": p.summary_of_apartments,
                "all_parking_details": p.all_parking_details,
                "last_modified": p.last_modified,
                "commencing_from": p.commencing_from,
                "leftmost_date": p.leftmost_date,
                "ending_with": p.ending_with,
            }

        total_bldgs = 0
        if p and p.building_details and isinstance(p.building_details, dict):
            id_list = p.building_details.get("Identification of Building", [])
            total_bldgs = len(id_list) if isinstance(id_list, list) else 1

        items.append(ScrapedProjectItem(
            rera_id=rid,
            project_name=p.project_name if p else dec.get("project_name", ""),
            project_status=p.project_status if p else "Active",
            project_type=p.project_type if p else "Residential",
            district=p.district if p else job.district_name,
            taluka=p.taluka if p else None,
            locality=p.locality if p else None,
            pin_code=p.pin_code if p else None,
            promoter_details=p.promoter_details if p else None,
            proposed_completion_date=str((p.project_completion_date_revised or p.project_completion_date_original) if p else ""),
            last_modified=p.last_modified if p else dec.get("website_last_modified"),
            website_last_modified=dec.get("website_last_modified"),
            stored_last_modified=dec.get("existing_last_modified") or dec.get("stored_last_modified"),
            action=dec.get("action", "Scraped"),
            decision_status=dec.get("status", "NEW"),
            total_buildings=total_bldgs,
            bank_name=p.bank_name if p else None,
            raw_data=raw,
        ))

    # Fallback to include any db_projects
    for p in db_projects:
        rid_up = (p.rera_id or "").strip().upper()
        if rid_up not in processed_ids:
            processed_ids.add(rid_up)
            total_bldgs = 0
            if p.building_details and isinstance(p.building_details, dict):
                id_list = p.building_details.get("Identification of Building", [])
                total_bldgs = len(id_list) if isinstance(id_list, list) else 1
            raw = {
                "rera_id": p.rera_id,
                "project_name": p.project_name,
                "project_status": p.project_status,
                "district": p.district,
                "promoter_details": p.promoter_details,
                "bank_name": p.bank_name,
                "building_details": p.building_details,
                "bhk_details": p.bhk_details,
                "last_modified": p.last_modified,
            }
            items.append(ScrapedProjectItem(
                rera_id=p.rera_id,
                project_name=p.project_name,
                project_status=p.project_status,
                project_type=p.project_type,
                district=p.district,
                taluka=p.taluka,
                locality=p.locality,
                pin_code=p.pin_code,
                promoter_details=p.promoter_details,
                proposed_completion_date=str(p.project_completion_date_revised or p.project_completion_date_original or ""),
                last_modified=p.last_modified,
                action="Scraped & Committed",
                decision_status="SCRAPED_OK",
                total_buildings=total_bldgs,
                bank_name=p.bank_name,
                raw_data=raw,
            ))

    export_files = {
        "csv": f"/api/scraper/jobs/{job_id}/export?format=csv",
        "excel": f"/api/scraper/jobs/{job_id}/export?format=excel",
        "json": f"/api/scraper/jobs/{job_id}/export?format=json",
        "sql": f"/api/scraper/jobs/{job_id}/export?format=sql",
    }

    scraped_count = sum(1 for it in items if it.decision_status in ("NEW", "UPDATED_RESCRAPPED", "SCRAPED_OK"))
    skipped_count = sum(1 for it in items if it.decision_status == "UNCHANGED_SKIPPED")
    failed_count = sum(1 for it in items if it.decision_status == "FAILED")

    return JobScrapedDataResponse(
        job_id=job.job_id,
        district_name=job.district_name,
        total_count=len(items),
        scraped_count=scraped_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        projects=items,
        export_files=export_files,
    )


@router.get("/jobs/{job_id}/export")
def export_scraping_job_data(
    job_id: str,
    format: str = Query("csv", pattern="^(csv|excel|xlsx|json|sql)$"),
    db: Session = Depends(get_db)
):
    """Export or download complete dataset extracted for a scraping job."""
    from app.models.models import Project, ScrapeJob

    job = db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    fmt = "xlsx" if format in ("excel", "xlsx") else format.lower()
    clean_dist = re.sub(r'[^\w\-]+', '_', job.district_name.strip()).strip('_') if job.district_name else "All_Maharashtra"

    # 1. Search disk for generated output files
    search_dirs = [
        CSV_PROCESSED_DIR / clean_dist if fmt in ("csv", "sql") else EXCEL_PROCESSED_DIR / clean_dist,
        CSV_PROCESSED_DIR if fmt in ("csv", "sql") else EXCEL_PROCESSED_DIR,
    ]
    for d in search_dirs:
        if d.exists():
            for f in d.glob(f"*{job_id}*.{fmt}"):
                return FileResponse(str(f), filename=f.name, media_type="application/octet-stream")
            for f in d.glob(f"*.{fmt}"):
                if clean_dist.lower() in f.name.lower():
                    return FileResponse(str(f), filename=f.name, media_type="application/octet-stream")

    # 2. Dynamic generation fallback directly from database
    summary = job.summary_json or {}
    project_records = summary.get("project_records") or []
    rera_ids = [pr.get("rera_id") for pr in project_records if pr.get("rera_id")]

    query = db.query(Project)
    if rera_ids:
        query = query.filter(Project.rera_id.in_(rera_ids))
    elif job.district_name and job.district_name.lower() not in ("all", "all / any district", ""):
        query = query.filter(Project.district.ilike(f"%{job.district_name.strip()}%"))

    projects = query.all()

    rows = []
    for p in projects:
        rows.append({
            "RERA ID": p.rera_id,
            "Project Name": p.project_name,
            "Project Status": p.project_status,
            "Project Type": p.project_type,
            "District": p.district,
            "Taluka": p.taluka,
            "Locality": p.locality,
            "Pin Code": p.pin_code,
            "Promoter Details": p.promoter_details,
            "Proposed Completion Date Original": str(p.project_completion_date_original or ""),
            "Proposed Completion Date Revised": str(p.project_completion_date_revised or ""),
            "Bank Name": p.bank_name,
            "IFSC Code": p.ifsc_code,
            "Bank Address": p.bank_address,
            "Last Modified": p.last_modified,
            "Commencing From": p.commencing_from,
            "Ending With": p.ending_with,
        })
    df = pd.DataFrame(rows)

    if fmt == "csv":
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="MahaRERA_{clean_dist}_{job_id}.csv"'}
        )
    elif fmt == "xlsx":
        import io
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="MahaRERA_{clean_dist}_{job_id}.xlsx"'}
        )
    elif fmt == "json":
        return Response(
            content=json.dumps(rows, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="MahaRERA_{clean_dist}_{job_id}.json"'}
        )
    else:
        sql_lines = [f"-- MahaRERA SQL Export for Job {job_id} ({job.district_name})", "BEGIN;"]
        for p in projects:
            p_n = (p.project_name or "").replace("'", "''")
            p_d = (p.district or "").replace("'", "''")
            p_s = (p.project_status or "").replace("'", "''")
            sql_lines.append(f"INSERT INTO projects (rera_id, project_name, district, project_status) VALUES ('{p.rera_id}', '{p_n}', '{p_d}', '{p_s}') ON CONFLICT (rera_id) DO NOTHING;")
        sql_lines.append("COMMIT;")
        return Response(
            content="\n".join(sql_lines).encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="MahaRERA_{clean_dist}_{job_id}.sql"'}
        )

