"""Data cleaning, normalization, and validation engine for MahaRERA projects.

Validates RERA ID format, geospatial coordinates within Maharashtra boundaries,
parses multi-format dates, normalizes districts and statuses, and detects data quality issues.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


from app.processing.transformer import transform_raw_to_standard_jsonb


def parse_dict_or_json(val: Any) -> Dict[str, Any]:
    """Parse dictionary from dict, JSON string, or Python string representation."""
    if not val or val == "None":
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str or val_str in ("{}", "[]", "None", "nan", "null"):
            return {}
        try:
            res = json.loads(val_str)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        try:
            res = ast.literal_eval(val_str)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
    return {}


def parse_date(val: Any) -> Optional[date]:
    """Parse date from common formats found in MahaRERA portal or PDF certificates."""
    if not val or val == "None":
        return None
    val_str = str(val).strip()
    if not val_str:
        return None

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_float(val: Any) -> Optional[float]:
    """Safely parse float coordinate or area."""
    if val is None or val == "" or str(val).strip().lower() in ("none", "null", "nan"):
        return None
    try:
        # Remove any non-numeric characters except . and -
        cleaned = re.sub(r"[^\d.-]", "", str(val).strip())
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def normalize_district(district: Optional[str]) -> Optional[str]:
    """Normalize Maharashtra district name."""
    if not district:
        return None
    d = " ".join(str(district).strip().split())
    # Handle common casing or slight spelling variations
    d_title = d.title()
    corrections = {
        "Raigad": "Raigarh",
        "Mumbai": "Mumbai City",
        "Bombay": "Mumbai City",
        "Suburban Mumbai": "Mumbai Suburban",
    }
    return corrections.get(d_title, d_title)


def validate_project_record(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], str]:
    """Validate and clean a raw project dictionary.
    
    Returns:
        (cleaned_dict, error_list, validation_status)
    """
    cleaned: Dict[str, Any] = {}
    errors: List[str] = []

    # 1. RERA ID validation
    raw_rera_id = raw.get("Registration Number") or raw.get("Rera ID") or raw.get("rera_id")
    if not raw_rera_id:
        errors.append("Missing RERA Registration Number")
        rera_id = "UNKNOWN"
    else:
        rera_id = str(raw_rera_id).strip()
        if not (rera_id.startswith("P") and len(rera_id) >= 11 and rera_id[1:12].isdigit()):
            errors.append(f"Invalid RERA ID format: '{rera_id}' (expected P followed by 11 digits)")

    cleaned["rera_id"] = rera_id
    cleaned["registration_number"] = rera_id

    # 2. Text fields
    cleaned["project_name"] = str(raw.get("Project Name") or raw.get("project_name") or "").strip() or None
    cleaned["project_location"] = str(raw.get("Project Location") or raw.get("project_location") or "").strip() or None
    cleaned["project_type"] = str(raw.get("Project Type") or raw.get("project_type") or "").strip() or None
    cleaned["project_status"] = str(raw.get("ProjectStatus") or raw.get("project_status") or "").strip() or None

    # 3. Location fields
    raw_district = raw.get("District") or raw.get("district")
    cleaned["district"] = normalize_district(raw_district)
    cleaned["taluka"] = str(raw.get("Taluka") or raw.get("taluka") or "").strip() or None
    cleaned["village"] = str(raw.get("Village") or raw.get("village") or "").strip() or None
    cleaned["state_ut"] = str(raw.get("State_UT") or raw.get("state_ut") or "Maharashtra").strip() or None
    cleaned["locality"] = str(raw.get("Locality") or raw.get("locality") or "").strip() or None
    cleaned["pin_code"] = str(raw.get("Pin_Code") or raw.get("pin_code") or "").strip() or None
    cleaned["survey_no"] = str(raw.get("survey_no") or "").strip() or None

    # 4. Geospatial validation (Maharashtra coordinates: Lat ~15.5 to 22.5, Lon ~72.5 to 81.0)
    lat = parse_float(raw.get("Latitude") or raw.get("latitude"))
    lon = parse_float(raw.get("Longitude") or raw.get("longitude"))

    if lat is not None and lon is not None:
        # Validate coordinates lie roughly within Maharashtra or neighboring region
        if 15.0 <= lat <= 23.0 and 72.0 <= lon <= 81.5:
            cleaned["latitude"] = lat
            cleaned["longitude"] = lon
        else:
            errors.append(f"Coordinates ({lat}, {lon}) are outside Maharashtra bounding box")
            cleaned["latitude"] = None
            cleaned["longitude"] = None
    else:
        cleaned["latitude"] = None
        cleaned["longitude"] = None

    # 5. Area details
    cleaned["total_land_area"] = str(raw.get("Total Land Area") or raw.get("total_land_area") or "").strip() or None
    cleaned["aggregate_area"] = str(raw.get("Aggregate area") or raw.get("aggregate_area") or "").strip() or None
    cleaned["land_area_applied"] = str(raw.get("Land Area for Project Applied for this Registration") or raw.get("land_area_applied") or "").strip() or None
    cleaned["permissible_builtup_area"] = str(raw.get("Permissible Builtup Area") or raw.get("permissible_builtup_area") or "").strip() or None
    cleaned["sanctioned_builtup_area"] = str(raw.get("Sanctioned Builtup Area") or raw.get("sanctioned_builtup_area") or "").strip() or None

    # 6. Dates
    cleaned["date_of_registration"] = parse_date(raw.get("Date of Registration") or raw.get("date_of_registration"))
    cleaned["project_completion_date_original"] = parse_date(raw.get("Project proposed completion date original") or raw.get("project_completion_date_original"))
    cleaned["project_completion_date_revised"] = parse_date(raw.get("Project proposed completion date revised") or raw.get("project_completion_date_revised"))

    # 7. Boundaries
    cleaned["boundaries_east"] = str(raw.get("Boundaries_East") or raw.get("boundaries_east") or "").strip() or None
    cleaned["boundaries_west"] = str(raw.get("Boundaries_West") or raw.get("boundaries_west") or "").strip() or None
    cleaned["boundaries_south"] = str(raw.get("Boundaries_South") or raw.get("boundaries_south") or "").strip() or None
    cleaned["boundaries_north"] = str(raw.get("Boundaries_North") or raw.get("boundaries_north") or "").strip() or None

    # 8. Promoter & legal
    cleaned["promoter_details"] = str(raw.get("Promoter_Details") or raw.get("promoter_details") or "").strip() or None
    cleaned["has_investors"] = str(raw.get("Are there any Investor other than the Promoter in the Project") or raw.get("has_investors") or "").strip() or None
    cleaned["past_experience_info"] = str(raw.get("past_experience_info") or "").strip() or None
    cleaned["litigations"] = str(raw.get("Litigations related to the project ?") or raw.get("litigations") or "").strip() or None

    # 9. Bank details
    cleaned["bank_name"] = str(raw.get("Bank Name") or raw.get("bank_name") or "").strip() or None
    cleaned["ifsc_code"] = str(raw.get("IFSC Code") or raw.get("ifsc_code") or "").strip() or None
    cleaned["bank_address"] = str(raw.get("Bank Address") or raw.get("bank_address") or "").strip() or None

    # 10. Standardized JSONB structures (Normalized for PostgreSQL storage)
    raw_bhk = raw.get("bhk_details")
    raw_bld = raw.get("building_details")
    raw_apt = raw.get("Summary_of_Apartments/Units") or raw.get("summary_of_apartments")
    raw_pkg = raw.get("All_Parking_Details") or raw.get("all_parking_details")

    transformed = transform_raw_to_standard_jsonb(
        bhk_raw=raw_bhk,
        building_raw=raw_bld,
        summary_raw=raw_apt,
        parking_raw=raw_pkg,
        project_metadata={
            "rera_id": rera_id,
            "registration_number": rera_id,
            "project_name": cleaned.get("project_name"),
            "district": cleaned.get("district"),
            "bank_name": cleaned.get("bank_name"),
            "ifsc_code": cleaned.get("ifsc_code"),
            "bank_address": cleaned.get("bank_address")
        }
    )

    cleaned["bhk_details"] = transformed["bhk_details"]
    cleaned["building_details"] = transformed["building_details"]
    cleaned["summary_of_apartments"] = transformed["summary_of_apartments"]
    cleaned["all_parking_details"] = transformed["all_parking_details"]
    cleaned["units_json"] = transformed["units_json"]

    # 11. Scraper / Certificate metadata
    cleaned["organization"] = str(raw.get("Organization") or raw.get("organization") or "").strip() or None
    cleaned["last_modified"] = str(raw.get("Last_Modified") or raw.get("last_modified") or "").strip() or None
    cleaned["commencing_from"] = str(raw.get("Commencing From") or raw.get("commencing_from") or "").strip() or None
    cleaned["leftmost_date"] = str(raw.get("Leftmost Date") or raw.get("leftmost_date") or "").strip() or None
    cleaned["ending_with"] = str(raw.get("Ending With") or raw.get("ending_with") or "").strip() or None
    cleaned["cert_date_source"] = str(raw.get("Cert_Date_Source") or raw.get("cert_date_source") or "").strip() or None
    cleaned["source_url"] = str(raw.get("source_url") or "").strip() or None

    # Determine certificate extraction status
    cert_src = cleaned["cert_date_source"] or ""
    if "PDF_TEXT" in cert_src:
        cleaned["cert_extraction_status"] = "parsed"
    elif "OCR" in cert_src:
        cleaned["cert_extraction_status"] = "ocr_processed"
    elif cleaned["commencing_from"] or cleaned["ending_with"]:
        cleaned["cert_extraction_status"] = "downloaded"
    elif "NOT_READ" in cert_src:
        cleaned["cert_extraction_status"] = "failed"
    else:
        cleaned["cert_extraction_status"] = "not_attempted"

    # 12. Overall validation status
    if not errors and cleaned["rera_id"] != "UNKNOWN" and cleaned["project_name"]:
        status = "VALID"
    elif errors and (cleaned["rera_id"] == "UNKNOWN" or not cleaned["project_name"]):
        status = "INVALID"
    else:
        status = "PARTIAL"

    cleaned["validation_status"] = status
    cleaned["validation_errors"] = errors

    return cleaned, errors, status

