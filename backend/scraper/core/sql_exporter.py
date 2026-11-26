"""RERA INSIGHT - PostgreSQL & PL/pgSQL Script Exporter.

Exports scraped MahaRERA records to production-ready PostgreSQL / PL/pgSQL (.sql) script
with table DDL, PL/pgSQL validation triggers, and ON CONFLICT DO UPDATE upsert statements.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd


def _escape_sql_val(val: Any) -> str:
    """Format a Python value as a valid PostgreSQL literal."""
    if val is None or pd.isna(val) or val == "" or str(val).strip().lower() in ("none", "null", "nan"):
        return "NULL"

    if isinstance(val, (int, float)):
        return str(val)

    if isinstance(val, (date, datetime)):
        return f"'{val.strftime('%Y-%m-%d')}'"

    if isinstance(val, (dict, list)):
        dumped = json.dumps(val, ensure_ascii=False)
        return f"$${dumped}$$::jsonb"

    val_str = str(val).strip()

    # Check if string looks like JSON
    if (val_str.startswith("{") and val_str.endswith("}")) or (val_str.startswith("[") and val_str.endswith("]")):
        return f"$${val_str}$$::jsonb"

    # Use dollar-quoting for strings containing quotes or multiline text
    if "'" in val_str or "\n" in val_str or "\r" in val_str or "\\" in val_str:
        return f"$${val_str}$$"

    return f"'{val_str}'"


def generate_postgresql_dump(
    records: List[Dict[str, Any]],
    output_sql_path: Union[str, Path],
    job_id: str = "export",
) -> Path:
    """Generate a standalone .sql file executable in PostgreSQL / pgAdmin / DBeaver / psql."""
    out_path = Path(output_sql_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Standard column mapping from MahaRERA scraped fields to PostgreSQL table
    sql_lines = [
        "-- ====================================================================",
        "-- RERA INSIGHT: PostgreSQL & PL/pgSQL Project Ingestion Script",
        f"-- Generated At: {datetime.now().isoformat()}",
        f"-- Scrape Job:   {job_id}",
        f"-- Total Rows:   {len(records)}",
        "-- ====================================================================",
        "",
        "BEGIN;",
        "",
        "-- Ensure schema and tables exist",
        "CREATE TABLE IF NOT EXISTS projects (",
        "    rera_id VARCHAR(32) PRIMARY KEY,",
        "    registration_number VARCHAR(64),",
        "    date_of_registration DATE,",
        "    project_name VARCHAR(255),",
        "    project_location TEXT,",
        "    project_type VARCHAR(64),",
        "    project_status VARCHAR(64),",
        "    district VARCHAR(64),",
        "    taluka VARCHAR(64),",
        "    village VARCHAR(128),",
        "    state_ut VARCHAR(64) DEFAULT 'MAHARASHTRA',",
        "    locality VARCHAR(255),",
        "    pin_code VARCHAR(16),",
        "    longitude NUMERIC(10, 6),",
        "    latitude NUMERIC(10, 6),",
        "    survey_no VARCHAR(255),",
        "    total_land_area VARCHAR(64),",
        "    permissible_builtup_area VARCHAR(64),",
        "    sanctioned_builtup_area VARCHAR(64),",
        "    project_completion_date_original DATE,",
        "    project_completion_date_revised DATE,",
        "    boundaries_east TEXT,",
        "    boundaries_west TEXT,",
        "    boundaries_south TEXT,",
        "    boundaries_north TEXT,",
        "    promoter_details TEXT,",
        "    has_investors VARCHAR(16),",
        "    past_experience_info TEXT,",
        "    litigations TEXT,",
        "    bank_name VARCHAR(128),",
        "    ifsc_code VARCHAR(32),",
        "    bank_address TEXT,",
        "    bhk_details JSONB,",
        "    building_details JSONB,",
        "    summary_of_apartments JSONB,",
        "    all_parking_details JSONB,",
        "    organization VARCHAR(128),",
        "    last_modified VARCHAR(64),",
        "    commencing_from DATE,",
        "    leftmost_date DATE,",
        "    ending_with DATE,",
        "    cert_date_source VARCHAR(64),",
        "    source_url TEXT,",
        "    scrape_job_id VARCHAR(64),",
        "    validation_status VARCHAR(32) DEFAULT 'VALID',",
        "    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,",
        "    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
        ");",
        "",
        "-- PL/pgSQL Validation Trigger",
        "CREATE OR REPLACE FUNCTION validate_project_record()",
        "RETURNS TRIGGER AS $$",
        "BEGIN",
        "    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN",
        "        IF NEW.latitude < 15.60 OR NEW.latitude > 22.05 OR NEW.longitude < 72.60 OR NEW.longitude > 80.90 THEN",
        "            NEW.validation_status := 'INVALID_COORDINATES';",
        "        ELSE",
        "            NEW.validation_status := 'VALID';",
        "        END IF;",
        "    END IF;",
        "    NEW.updated_at = CURRENT_TIMESTAMP;",
        "    RETURN NEW;",
        "END;",
        "$$ LANGUAGE plpgsql;",
        "",
        "DROP TRIGGER IF EXISTS trg_validate_project ON projects;",
        "CREATE TRIGGER trg_validate_project",
        "BEFORE INSERT OR UPDATE ON projects",
        "FOR EACH ROW",
        "EXECUTE FUNCTION validate_project_record();",
        "",
        "-- Insert / Upsert Scraped Project Records",
    ]

    for rec in records:
        # Resolve RERA ID
        rera_id = rec.get("Rera ID") or rec.get("Registration Number") or rec.get("rera_id")
        if not rera_id or pd.isna(rera_id):
            continue

        rera_id_clean = str(rera_id).strip()

        col_map = {
            "rera_id": rera_id_clean,
            "registration_number": rec.get("Registration Number") or rec.get("registration_number") or rera_id_clean,
            "date_of_registration": rec.get("Date of Registration") or rec.get("date_of_registration"),
            "project_name": rec.get("Project Name") or rec.get("project_name"),
            "project_location": rec.get("Project Location") or rec.get("project_location"),
            "project_type": rec.get("Project Type") or rec.get("project_type"),
            "project_status": rec.get("ProjectStatus") or rec.get("project_status"),
            "district": rec.get("District") or rec.get("district"),
            "taluka": rec.get("Taluka") or rec.get("taluka"),
            "village": rec.get("Village") or rec.get("village"),
            "state_ut": rec.get("State_UT") or rec.get("state_ut") or "MAHARASHTRA",
            "locality": rec.get("Locality") or rec.get("locality"),
            "pin_code": rec.get("Pin_Code") or rec.get("pin_code"),
            "longitude": rec.get("Longitude") or rec.get("longitude"),
            "latitude": rec.get("Latitude") or rec.get("latitude"),
            "survey_no": rec.get("survey_no"),
            "total_land_area": rec.get("Total Land Area") or rec.get("total_land_area"),
            "permissible_builtup_area": rec.get("Permissible Builtup Area") or rec.get("permissible_builtup_area"),
            "sanctioned_builtup_area": rec.get("Sanctioned Builtup Area") or rec.get("sanctioned_builtup_area"),
            "project_completion_date_original": rec.get("Project proposed completion date original") or rec.get("project_completion_date_original"),
            "project_completion_date_revised": rec.get("Project proposed completion date revised") or rec.get("project_completion_date_revised"),
            "boundaries_east": rec.get("Boundaries_East") or rec.get("boundaries_east"),
            "boundaries_west": rec.get("Boundaries_West") or rec.get("boundaries_west"),
            "boundaries_south": rec.get("Boundaries_South") or rec.get("boundaries_south"),
            "boundaries_north": rec.get("Boundaries_North") or rec.get("boundaries_north"),
            "promoter_details": rec.get("Promoter_Details") or rec.get("promoter_details"),
            "has_investors": rec.get("Are there any Investor other than the Promoter in the Project") or rec.get("has_investors"),
            "past_experience_info": rec.get("past_experience_info"),
            "litigations": rec.get("Litigations related to the project ?") or rec.get("litigations"),
            "bank_name": rec.get("Bank Name") or rec.get("bank_name"),
            "ifsc_code": rec.get("IFSC Code") or rec.get("ifsc_code"),
            "bank_address": rec.get("Bank Address") or rec.get("bank_address"),
            "organization": rec.get("Organization") or rec.get("organization"),
            "last_modified": rec.get("Last_Modified") or rec.get("last_modified"),
            "commencing_from": rec.get("Commencing From") or rec.get("commencing_from"),
            "leftmost_date": rec.get("Leftmost Date") or rec.get("leftmost_date"),
            "ending_with": rec.get("Ending With") or rec.get("ending_with"),
            "cert_date_source": rec.get("Cert_Date_Source") or rec.get("cert_date_source"),
            "source_url": rec.get("source_url"),
            "scrape_job_id": job_id,
        }

        # JSON fields
        for json_key, possible_keys in [
            ("bhk_details", ["bhk_details", "bhk_details_part2"]),
            ("building_details", ["building_details"]),
            ("summary_of_apartments", ["Summary_of_Apartments/Units", "summary_of_apartments"]),
            ("all_parking_details", ["All_Parking_Details", "all_parking_details"]),
        ]:
            for pk in possible_keys:
                if rec.get(pk) and not pd.isna(rec.get(pk)):
                    col_map[json_key] = rec.get(pk)
                    break

        cols = list(col_map.keys())
        escaped_vals = [_escape_sql_val(col_map[c]) for c in cols]

        update_assignments = [f"    {c} = EXCLUDED.{c}" for c in cols if c != "rera_id"]

        stmt = (
            f"INSERT INTO projects ({', '.join(cols)})\n"
            f"VALUES ({', '.join(escaped_vals)})\n"
            f"ON CONFLICT (rera_id) DO UPDATE SET\n"
            f"{',\n'.join(update_assignments)},\n"
            f"    updated_at = CURRENT_TIMESTAMP;\n"
        )
        sql_lines.append(stmt)

    sql_lines.append("COMMIT;")
    sql_lines.append("")

    content = "\n".join(sql_lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    return out_path

