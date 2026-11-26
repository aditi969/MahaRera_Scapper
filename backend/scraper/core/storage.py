"""Centralized File Storage Manager for Scraper module."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

# Resolve directory
_DIR = Path(__file__).resolve()
# parents[0] = core, parents[1] = scraper, parents[2] = backend, parents[3] = project root
BACKEND_ROOT = _DIR.parents[2]
PROJECT_ROOT = _DIR.parents[3] if len(_DIR.parents) > 3 else BACKEND_ROOT

# Centralized storage directory inside backend/storage
STORAGE_DIR = BACKEND_ROOT / "storage"


CSV_RAW_DIR = STORAGE_DIR / "csv" / "raw"
CSV_PROCESSED_DIR = STORAGE_DIR / "csv" / "processed"
CSV_EXPORTS_DIR = STORAGE_DIR / "csv" / "exports"

EXCEL_RAW_DIR = STORAGE_DIR / "excel" / "raw"
EXCEL_PROCESSED_DIR = STORAGE_DIR / "excel" / "processed"
EXCEL_EXPORTS_DIR = STORAGE_DIR / "excel" / "exports"

TEMP_DIR = STORAGE_DIR / "temp"
LOGS_DIR = BACKEND_ROOT / "logs"


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
