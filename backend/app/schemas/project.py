"""Pydantic v2 schemas for Project endpoints."""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rera_id: str
    registration_number: Optional[str] = None
    date_of_registration: Optional[date] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    project_status: Optional[str] = None
    district: Optional[str] = None
    taluka: Optional[str] = None
    village: Optional[str] = None
    locality: Optional[str] = None
    organization: Optional[str] = None
    promoter_details: Optional[str] = None
    project_completion_date_original: Optional[date] = None
    project_completion_date_revised: Optional[date] = None
    validation_status: Optional[str] = None
    created_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rera_id: str
    registration_number: Optional[str] = None
    date_of_registration: Optional[date] = None
    project_name: Optional[str] = None
    project_location: Optional[str] = None
    project_type: Optional[str] = None
    project_status: Optional[str] = None
    district: Optional[str] = None
    taluka: Optional[str] = None
    village: Optional[str] = None
    state_ut: Optional[str] = None
    locality: Optional[str] = None
    pin_code: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    survey_no: Optional[str] = None
    total_land_area: Optional[str] = None
    permissible_builtup_area: Optional[str] = None
    sanctioned_builtup_area: Optional[str] = None
    project_completion_date_original: Optional[date] = None
    project_completion_date_revised: Optional[date] = None
    boundaries_east: Optional[str] = None
    boundaries_west: Optional[str] = None
    boundaries_south: Optional[str] = None
    boundaries_north: Optional[str] = None
    promoter_details: Optional[str] = None
    has_investors: Optional[str] = None
    past_experience_info: Optional[str] = None
    litigations: Optional[str] = None
    bank_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_address: Optional[str] = None
    bhk_details: Optional[Dict[str, Any]] = None
    building_details: Optional[Dict[str, Any]] = None
    summary_of_apartments: Optional[Dict[str, Any]] = None
    all_parking_details: Optional[Dict[str, Any]] = None
    organization: Optional[str] = None
    last_modified: Optional[str] = None
    commencing_from: Optional[str] = None
    leftmost_date: Optional[str] = None
    ending_with: Optional[str] = None
    cert_date_source: Optional[str] = None
    source_url: Optional[str] = None
    scrape_job_id: Optional[str] = None
    is_duplicate: bool = False
    validation_status: Optional[str] = None
    validation_errors: Optional[List[Any]] = None
    extraction_errors: Optional[Dict[str, Any]] = None
    cert_extraction_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    data: List[ProjectListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
