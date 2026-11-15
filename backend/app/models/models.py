"""SQLAlchemy ORM models for RERA Insight."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base

# Universal JSON type that maps to native JSONB on PostgreSQL and JSON elsewhere
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Project(Base):
    __tablename__ = "projects"

    # Primary key
    rera_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)

    # Registration info
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_of_registration: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    project_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Location
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    taluka: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    village: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    state_ut: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locality: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pin_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    survey_no: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Area details
    total_land_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    permissible_builtup_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sanctioned_builtup_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Dates
    project_completion_date_original: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    project_completion_date_revised: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Boundaries
    boundaries_east: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    boundaries_west: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    boundaries_south: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    boundaries_north: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Promoter info
    promoter_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_investors: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    past_experience_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    litigations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bank details
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON fields
    bhk_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    building_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    summary_of_apartments: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    all_parking_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)

    # Search result metadata
    organization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    last_modified: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    commencing_from: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    leftmost_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ending_with: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cert_date_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scrape linkage
    scrape_job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("scrape_jobs.job_id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Data quality
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )
    validation_errors: Mapped[Optional[List[Any]]] = mapped_column(JSON_TYPE, nullable=True)
    extraction_errors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    cert_extraction_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    scrape_job: Mapped[Optional["ScrapeJob"]] = relationship(
        "ScrapeJob", back_populates="projects", foreign_keys=[scrape_job_id]
    )


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    job_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_code: Mapped[str] = mapped_column(String(20), nullable=False)
    start_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    end_page: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    headless: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_workers: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    projects_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    projects_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    projects_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_page: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    certificates_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    certificates_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="scrape_job", foreign_keys="Project.scrape_job_id"
    )
    logs: Mapped[List["ScrapeLog"]] = relationship(
        "ScrapeLog", back_populates="job", cascade="all, delete-orphan"
    )


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scrape_jobs.job_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(10), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationship
    job: Mapped["ScrapeJob"] = relationship("ScrapeJob", back_populates="logs")


class DataQualityCheck(Base):
    __tablename__ = "data_quality_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    valid_rera_ids: Mapped[int] = mapped_column(Integer, default=0)
    records_with_coordinates: Mapped[int] = mapped_column(Integer, default=0)
    records_missing_district: Mapped[int] = mapped_column(Integer, default=0)
    records_missing_completion_date: Mapped[int] = mapped_column(Integer, default=0)
    records_with_cert_dates: Mapped[int] = mapped_column(Integer, default=0)
    cert_extraction_rate: Mapped[float] = mapped_column(Float, default=0.0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_pass_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)
