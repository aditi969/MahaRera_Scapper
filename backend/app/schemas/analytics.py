"""Pydantic v2 schemas for Analytics and Data Quality endpoints."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_districts: int
    latest_scrape_date: Optional[datetime] = None


class DistrictStat(BaseModel):
    district: Optional[str]
    count: int


class StatusStat(BaseModel):
    status: Optional[str]
    count: int


class ProjectTypeStat(BaseModel):
    project_type: Optional[str]
    count: int


class TrendPoint(BaseModel):
    year: int
    month: Optional[int] = None
    count: int


class CompletionTrendPoint(BaseModel):
    year: int
    count: int


class ExtractionStatusStat(BaseModel):
    status: Optional[str]
    count: int


class DataQualityResponse(BaseModel):
    total_records: int
    valid_rera_ids: int
    records_with_coordinates: int
    records_missing_district: int
    records_missing_completion_date: int
    records_with_cert_dates: int
    cert_extraction_rate: float
    duplicate_count: int
    validation_pass_count: int
    validation_fail_count: int
    completeness_score: float
    by_extraction_status: List[ExtractionStatusStat]
