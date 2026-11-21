"""Centralized File Storage Manager for Scraper module."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

# Resolve root directory: d:\Rera Web App\scarpping\scarpping
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"

CSV_RAW_DIR = STORAGE_DIR / "csv" / "raw"
CSV_PROCESSED_DIR = STORAGE_DIR / "csv" / "processed"
CSV_EXPORTS_DIR = STORAGE_DIR / "csv" / "exports"

EXCEL_RAW_DIR = STORAGE_DIR / "excel" / "raw"
EXCEL_PROCESSED_DIR = STORAGE_DIR / "excel" / "processed"
EXCEL_EXPORTS_DIR = STORAGE_DIR / "excel" / "exports"

TEMP_DIR = STORAGE_DIR / "temp"
LOGS_DIR = PROJECT_ROOT / "logs"


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
    ):
        d.mkdir(parents=True, exist_ok=True)


def get_temp_file_path(filename: str) -> Path:
    """Return a path inside storage/temp/."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR / filename
