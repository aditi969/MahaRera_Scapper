"""Scraper job management API routes."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.scraper_repository import ScraperRepository
from app.schemas.scraper import ScrapeJobResponse, ScrapeLogResponse, StartJobRequest
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/scraper", tags=["Scraper Control"])


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

