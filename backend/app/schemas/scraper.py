"""Pydantic v2 schemas for Scraper endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StartJobRequest(BaseModel):
    district_name: str
    district_code: str
    start_page: int = Field(default=1, ge=1)
    end_page: int = Field(default=2, ge=1)
    headless: bool = True
    max_workers: int = Field(default=1, ge=1, le=2)

    @model_validator(mode="after")
    def validate_page_range(self) -> "StartJobRequest":
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
