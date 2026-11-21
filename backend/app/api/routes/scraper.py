"""Scraper job management API routes."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.scraper_repository import ScraperRepository
from app.schemas.scraper import (
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

