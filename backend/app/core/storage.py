"""Centralized File Storage Manager for RERA Insight.

Enforces clean, designated directory separation:
- storage/csv/raw
- storage/csv/processed
- storage/csv/exports
- storage/excel/raw
- storage/excel/processed
- storage/excel/exports
- storage/temp
- logs
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

# Resolve root directory: d:\Rera Web App\scarpping\scarpping
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STORAGE_DIR = PROJECT_ROOT / "storage"

CSV_RAW_DIR = STORAGE_DIR / "csv" / "raw"
CSV_PROCESSED_DIR = STORAGE_DIR / "csv" / "processed"
CSV_EXPORTS_DIR = STORAGE_DIR / "csv" / "exports"

EXCEL_RAW_DIR = STORAGE_DIR / "excel" / "raw"
EXCEL_PROCESSED_DIR = STORAGE_DIR / "excel" / "processed"
EXCEL_EXPORTS_DIR = STORAGE_DIR / "excel" / "exports"

TEMP_DIR = STORAGE_DIR / "temp"
LOGS_DIR = PROJECT_ROOT / "logs"
LEGACY_ARCHIVE_DIR = STORAGE_DIR / "archive" / "legacy_sqlite"


def ensure_all_storage_dirs():
    """Ensure all designated storage directories exist."""
    for d in (
        CSV_RAW_DIR,
        CSV_PROCESSED_DIR,
        CSV_EXPORTS_DIR,
        EXCEL_RAW_DIR,
        EXCEL_PROCESSED_DIR,
        EXCEL_EXPORTS_DIR,
        TEMP_DIR,
        LOGS_DIR,
        LEGACY_ARCHIVE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def get_job_storage_paths(job_id: str, prefix: str) -> Dict[str, Path]:
    """Return all standard file output paths for a scraping job located in their proper storage folders."""
    ensure_all_storage_dirs()
    return {
        "csv": CSV_PROCESSED_DIR / f"{prefix}.csv",
        "excel": EXCEL_PROCESSED_DIR / f"{prefix}.xlsx",
        "sql": CSV_PROCESSED_DIR / f"{prefix}.sql",
        "checkpoint": TEMP_DIR / f"checkpoint_{job_id}.json",
        "run_log": LOGS_DIR / f"run_log_{job_id}.txt",
        "failed_pages_csv": CSV_PROCESSED_DIR / f"failed_pages_{job_id}.csv",
        "failed_projects_csv": CSV_PROCESSED_DIR / f"failed_projects_{job_id}.csv",
    }


def get_temp_file_path(filename: str) -> Path:
    """Return a path inside storage/temp/."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR / filename
