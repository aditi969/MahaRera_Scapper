"""Pydantic v2 schemas for Scraper endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StartJobRequest(BaseModel):
    district_name: Optional[str] = "Raigarh"
    district_code: Optional[str] = "520"
    start_page: int = Field(default=1, ge=1)
    end_page: Optional[int] = Field(default=2, ge=1)
    scrape_all_pages: bool = False                     # Scrape entire website / all available pages
    headless: bool = True
    max_workers: int = Field(default=1, ge=1, le=2)

    # MahaRERA Search Filters
    project_type_category: str = "Registered Projects"  # "Registered Projects" | "Revoked Projects"
    search_query: Optional[str] = ""                   # Project Name or MahaRERA Registration Number
    pincode: Optional[str] = ""                        # 6-digit Pincode
    completion_date: Optional[str] = ""                # Completion Date string / YYYY-MM-DD
    state: Optional[str] = "MAHARASHTRA"               # State
    division: Optional[str] = ""                       # Division
    taluka: Optional[str] = ""                         # Taluka
    village: Optional[str] = ""                        # Village

    # Smart Scraping Controls
    smart_date_check: bool = True                      # Enable smart last-modified-date comparison

    @model_validator(mode="after")
    def validate_page_range(self) -> "StartJobRequest":
        if not self.scrape_all_pages:
            if self.end_page is None:
                raise ValueError("End page is required when page range is specified.")
            if self.end_page < self.start_page:
                raise ValueError("End page must be greater than or equal to start page.")
        return self


class ScrapeJobCreate(BaseModel):
    district_name: str
    district_code: str
    start_page: int = 1
    end_page: int = 5
    headless: bool = True
    max_workers: int = 2


class ScrapeJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    district_name: str
    district_code: str
    start_page: int
    end_page: int
    headless: bool
    max_workers: int
    status: str
    projects_found: int = 0
    projects_extracted: int = 0
    projects_failed: int = 0
    current_page: int = 1
    certificates_extracted: int = 0
    certificates_failed: int = 0
    filters_json: Optional[Dict[str, Any]] = None
    summary_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ScrapeLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    level: str
    message: str
    extra: Optional[Dict[str, Any]] = None
    created_at: datetime


class ScrapePreviewRequest(BaseModel):
    district_name: Optional[str] = None
    search_query: Optional[str] = None
    pincode: Optional[str] = None
    completion_date: Optional[str] = None
    project_type_category: Optional[str] = "Registered Projects"


class ScrapePreviewResponse(BaseModel):
    matching_in_database: int
    existing_projects: List[Dict[str, Any]]
    sample_records: List[Dict[str, Any]]
    filters_applied: Dict[str, Any]
