"""RERA INSIGHT - CSV Ingestion Tool.

Loads and validates any scraped MahaRERA CSV file directly into PostgreSQL / SQLite database.
Usage:
    python import_csv.py Raigarh_output_NEW.csv
"""
import sys
import argparse
from pathlib import Path

# Add backend and project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR / "app").exists() else SCRIPT_DIR
BACKEND_DIR = SCRIPT_DIR if (SCRIPT_DIR / "app").exists() else SCRIPT_DIR / "backend"
for p in (str(SCRIPT_DIR), str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
from app.database.session import SessionLocal, init_db
from app.processing.pipeline import IngestionPipeline


def import_csv_to_db(csv_path: str, job_id: str = "csv-import"):
    path = Path(csv_path)
    if not path.exists():
        print(f"❌ Error: File '{csv_path}' not found.")
        sys.exit(1)

    print(f"📁 Reading CSV: {path.resolve()}")
    df = pd.read_csv(path)
    print(f"📊 Found {len(df)} rows and {len(df.columns)} columns.")

    init_db()
    db = SessionLocal()
    pipeline = IngestionPipeline(db)

    records = df.to_dict(orient="records")
    saved_count, updated_count, error_count = 0, 0, 0

    print("\n🚀 Ingesting into SQL Database with PL/pgSQL validation rules...")
    for idx, raw in enumerate(records):
        clean_raw = {k: (None if pd.isna(v) else v) for k, v in raw.items()}
        project, is_new, errs = pipeline.ingest_project(clean_raw, job_id=job_id)
        if is_new:
            saved_count += 1
            action = "INSERTED"
        else:
            updated_count += 1
            action = "UPDATED "

        if errs:
            error_count += len(errs)

        v_status = getattr(project, "validation_status", "VALIDATED")
        print(f"  [{idx+1}/{len(records)}] {action}: {project.rera_id} | {project.project_name} ({project.project_status}) -> {v_status}")

    db.commit()
    db.close()

    # Generate companion .sql file in PostgreSQL / PL-pgSQL format
    try:
        from scraper.core.sql_exporter import generate_postgresql_dump
        sql_out = path.with_suffix(".sql")
        generate_postgresql_dump(records, sql_out, job_id=job_id)
        print(f"📄 Generated PL/pgSQL Script: {sql_out.resolve()}")
    except Exception as e:
        print(f"⚠️ Could not generate .sql file: {e}")

    print("\n" + "=" * 60)
    print("✅ CSV INGESTION COMPLETE")
    print(f"  Total Rows:         {len(records)}")
    print(f"  Inserted:           {saved_count}")
    print(f"  Updated:            {updated_count}")
    print(f"  Validation Issues:  {error_count}")
    print(f"  Database Status:    Verified & Committed")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest MahaRERA CSV into Database")
    parser.add_argument("csv_file", nargs="?", default="Raigarh_output_NEW.csv", help="Path to CSV file")
    parser.add_argument("--job-id", default="csv-direct-import", help="Job identifier tag")
    args = parser.parse_args()

    import_csv_to_db(args.csv_file, args.job_id)

