"""Date parsing, normalization, and comparison utilities for MahaRERA last-modified-date checks.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Tuple


def parse_date_str(date_str: Optional[str]) -> Optional[date]:
    """Parse a flexible date string into a datetime.date object.

    Handles formats:
      - YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
      - DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
      - MM/DD/YYYY, MM-DD-YYYY
      - Text dates like '18 Aug 2026', '18-Aug-2026'
    """
    if not date_str:
        return None

    s = str(date_str).strip()
    if not s or s.lower() in ("not available", "na", "n/a", "none", "null", "-", "undefined"):
        return None

    # Common standard formats
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d %b %Y",
        "%d-%b-%Y",
        "%d %B %Y",
        "%d-%B-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue

    # Regex fallback for YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m_iso:
        try:
            y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
            return date(y, m, d)
        except ValueError:
            pass

    # Regex fallback for DD-MM-YYYY
    m_in = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)
    if m_in:
        try:
            d, m, y = int(m_in.group(1)), int(m_in.group(2)), int(m_in.group(3))
            return date(y, m, d)
        except ValueError:
            pass

    return None


def normalize_date_display(date_str: Optional[str]) -> str:
    """Normalize a date string to standard YYYY-MM-DD format if possible, otherwise return trimmed string."""
    if not date_str:
        return "Not Available"
    d = parse_date_str(date_str)
    if d:
        return d.strftime("%Y-%m-%d")
    return str(date_str).strip()


def format_date_display(val: Optional[str | date]) -> str:
    """Format date to standard DD-MM-YYYY for display in logs and UI as specified."""
    if not val:
        return "Not Available"
    if isinstance(val, date):
        return val.strftime("%d-%m-%Y")
    s = str(val).strip()
    if s.lower() in ("not available", "na", "n/a", "none", "null", "-", "undefined", ""):
        return "Not Available"
    d = parse_date_str(s)
    if d:
        return d.strftime("%d-%m-%Y")
    return s


def compare_last_modified(
    existing_date_str: Optional[str],
    website_date_str: Optional[str]
) -> Tuple[str, str]:
    """Compare stored Last Modified Date with website's Last Modified Date.

    Conditions:
      - If existing date is not available / None -> 'NEW'
      - If existing date is present, but website date is missing/invalid -> 'UPDATED_RESCRAPED'
        (Handle missing or invalid dates separately. Do not automatically assume missing dates mean unchanged.)
      - If normalized dates match -> 'UNCHANGED_SKIPPED'
      - If normalized dates differ -> 'UPDATED_RESCRAPED'

    Returns:
        (decision, reason)
        decision is one of:
          - 'UNCHANGED_SKIPPED': Dates match -> Skip
          - 'UPDATED_RESCRAPED': Dates differ or either date is missing/invalid -> Re-scrape & Update
          - 'NEW': No existing date or existing date unavailable -> Scrape as new project
    """
    if not existing_date_str or str(existing_date_str).strip().lower() in ("not available", "na", "none", "null", "", "-"):
        return "NEW", "No previous last-modified date found"

    # Handle missing or invalid website date separately without assuming unchanged
    if not website_date_str or str(website_date_str).strip().lower() in ("not available", "na", "none", "null", "", "-"):
        return "UPDATED_RESCRAPED", "Missing or invalid Last Modified Date on website. Re-scraping project."

    s_existing = str(existing_date_str).strip()
    s_website = str(website_date_str).strip()

    # Exact string match (ignoring delimiter difference)
    if s_existing == s_website or s_existing.replace("/", "-") == s_website.replace("/", "-"):
        return "UNCHANGED_SKIPPED", "Date matches. Skipping project."

    d_existing = parse_date_str(s_existing)
    d_website = parse_date_str(s_website)

    if d_existing and d_website:
        if d_existing == d_website:
            return "UNCHANGED_SKIPPED", "Date matches. Skipping project."
        else:
            return "UPDATED_RESCRAPED", "Last Modified Date changed. Re-scraping project."

    # Unparseable fallback: if normalized alphanumeric strings match, treat as matching
    clean_exist = re.sub(r'[^a-zA-Z0-9]', '', s_existing).lower()
    clean_web = re.sub(r'[^a-zA-Z0-9]', '', s_website).lower()
    if clean_exist and clean_exist == clean_web:
        return "UNCHANGED_SKIPPED", "Date matches. Skipping project."

    # If unparseable and strings differ, do not assume unchanged
    return "UPDATED_RESCRAPED", "Missing or invalid Last Modified Date. Re-scraping project."
