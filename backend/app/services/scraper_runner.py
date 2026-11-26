"""Dedicated Scraper Runner Process.

Runs in an isolated process decoupled from FastAPI/Uvicorn, ensuring that
API reloads, file watchers, or server restarts do not interrupt active
Selenium browser sessions.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

# Ensure UTF-8 output encoding on Windows console/pipes to prevent UnicodeEncodeError on emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root and backend are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.database.session import SessionLocal
from app.models.models import Project, ScrapeJob, ScrapeLog
from app.processing.pipeline import IngestionPipeline
from app.repositories.scraper_repository import ScraperRepository
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger
from scraper.core.worker import ScraperWorker


def run_isolated_scraper(
    job_id: str,
    district_name: str,
    district_code: str,
    start_page: int,
    end_page: Optional[int],
    max_workers: int,
    headless: bool,
    project_type_category: str = "Registered Projects",
    search_query: str = "",
    pincode: str = "",
    completion_date: str = "",
    state: str = "MAHARASHTRA",
    division: str = "",
    taluka: str = "",
    village: str = "",
    smart_date_check: bool = True,
    scrape_all_pages: bool = False,
):
    print(f"[RUNNER] Starting isolated scrape process for Job {job_id} (PID: {os.getpid()})")

    # Own database session
    if not district_code and district_name:
        from scraper.core.navigation import MAHARASHTRA_DISTRICT_CODE_MAP
        district_code = MAHARASHTRA_DISTRICT_CODE_MAP.get(district_name.strip().lower(), "")

    db = SessionLocal()
    repo = ScraperRepository(db)
    pipeline = IngestionPipeline(db)

    # Preload existing projects from DB for smart date comparison
    existing_projects_map: Dict[str, Dict[str, Any]] = {}
    try:
        rows = db.query(Project.rera_id, Project.project_name, Project.last_modified).all()
        for r in rows:
            if r[0]:
                clean_id = str(r[0]).strip().upper()
                existing_projects_map[clean_id] = {
                    "rera_id": clean_id,
                    "project_name": str(r[1] or "").strip(),
                    "last_modified": str(r[2] or "").strip(),
                }
        print(f"[RUNNER] Preloaded {len(existing_projects_map)} projects from database for smart date check.")
    except Exception as db_err:
        print(f"[RUNNER] Could not preload DB projects for index: {db_err}")

    # Update job state to RUNNING
    try:
        job = repo.get_job(job_id)
        if job:
            job.status = "RUNNING"
            job.started_at = datetime.now()
            db.commit()
    except Exception as e:
        print(f"[RUNNER] Error updating job to RUNNING: {e}")

    def log_callback(level: str, msg: str):
        try:
            log_db = SessionLocal()
            log_repo = ScraperRepository(log_db)
            log_repo.add_log(job_id, level, msg)
            log_db.commit()
            log_db.close()
        except Exception:
            pass
        try:
            print(f"[{level}] {msg}", flush=True)
        except Exception:
            try:
                safe_msg = msg.encode("ascii", "replace").decode("ascii")
                print(f"[{level}] {safe_msg}", flush=True)
            except Exception:
                pass

    def progress_callback(event: Dict[str, Any]):
        event_type = event.get("type")
        try:
            update_db = SessionLocal()
            job_rec = update_db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
            if job_rec:
                if event_type == "page_started":
                    job_rec.current_page = event.get("page", job_rec.current_page)
                elif event_type == "project_extracted":
                    job_rec.projects_extracted = (job_rec.projects_extracted or 0) + 1
                elif event_type == "project_failed":
                    job_rec.projects_failed = (job_rec.projects_failed or 0) + 1

                # Live synchronization of all smart metric counters on every event
                try:
                    live_stats = worker.checkpoint_manager.get_summary_stats()
                    job_rec.summary_json = live_stats
                    disc = live_stats.get("total_discovered", 0)
                    suc = live_stats.get("successfully_scraped", 0) or live_stats.get("successful_scraped", 0)
                    saved = live_stats.get("total_saved_or_updated", 0)
                    rec_len = len(live_stats.get("project_records", []))
                    
                    if disc > 0:
                        job_rec.projects_found = max(disc, job_rec.projects_found or 0)
                    # projects_extracted in DB represents projects successfully scraped / processed in this job
                    job_rec.projects_extracted = max(suc, saved, rec_len, job_rec.projects_extracted or 0)
                    if live_stats.get("failed_projects", 0) > 0:
                        job_rec.projects_failed = live_stats["failed_projects"]

                    # Stream live stats to WebSocket subscribers via stdout
                    print(f"__JOB_STATS__:{json.dumps(live_stats)}", flush=True)
                except Exception:
                    pass

                if event_type == "job_summary":
                    job_rec.summary_json = event.get("summary")
                    summary = event.get("summary") or {}
                    if "total_discovered" in summary:
                        job_rec.projects_found = summary["total_discovered"]
                update_db.commit()
            update_db.close()
        except Exception as prog_e:
            print(f"[RUNNER] Progress update error: {prog_e}")

    def record_scraped_callback(row_dict: Dict[str, Any]):
        try:
            pipeline.ingest_project(row_dict, job_id=job_id)
            db.commit()

            # Stream live scraped project details to frontend in real time
            clean_rera_id = str(row_dict.get("Registration Number") or row_dict.get("Rera ID") or row_dict.get("rera_id") or "").strip()
            p_name = str(row_dict.get("Project Name") or row_dict.get("project_name") or "").strip()
            p_status = str(row_dict.get("ProjectStatus") or row_dict.get("Project Status") or "Active").strip()
            p_district = str(row_dict.get("District") or district_name or "").strip()
            p_comp = str(row_dict.get("Project proposed completion date revised") or row_dict.get("Project proposed completion date original") or "").strip()

            total_bldgs = 0
            bld_info = row_dict.get("building_details")
            if isinstance(bld_info, dict):
                id_list = bld_info.get("Identification of Building", [])
                total_bldgs = len(id_list) if isinstance(id_list, list) else 1

            live_record = {
                "rera_id": clean_rera_id,
                "project_name": p_name,
                "project_status": p_status,
                "district": p_district,
                "completion_date": p_comp,
                "promoter_details": str(row_dict.get("Promoter_Details") or "")[:120],
                "action": "SCRAPED_OK",
                "decision_status": "NEW" if clean_rera_id not in existing_projects_map else "UPDATED",
                "total_buildings": total_bldgs,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            print(f"__PROJECT_SCRAPED__:{json.dumps(live_record)}", flush=True)
        except Exception as ing_e:
            db.rollback()
            log_callback("WARNING", f"Database incremental upsert error: {ing_e}")

    # Configure scraper with performance bounds and organized city/search folder structure
    import re
    import shutil

    # Determine dedicated city / filter folder
    # Priority: District Name > Search Query > Pincode > All_Maharashtra
    clean_dist = re.sub(r'[^\w\-]+', '_', district_name.strip()).strip('_') if district_name and district_name.strip() not in ("All / Any District", "All", "") else ""
    clean_q = re.sub(r'[^\w\-]+', '_', search_query.strip()).strip('_')[:30] if search_query and search_query.strip() else ""
    clean_pin = re.sub(r'[^\w\-]+', '_', pincode.strip()).strip('_') if pincode and pincode.strip() else ""

    if clean_dist:
        folder_name = clean_dist
    elif clean_q:
        folder_name = f"Search_{clean_q}"
    elif clean_pin:
        folder_name = f"Pincode_{clean_pin}"
    else:
        folder_name = "All_Maharashtra"

    from app.core.storage import (
        CSV_PROCESSED_DIR,
        EXCEL_PROCESSED_DIR,
        TEMP_DIR,
        LOGS_DIR,
        ensure_all_storage_dirs,
    )
    ensure_all_storage_dirs()

    # Dedicated folder within storage/csv/processed and storage/excel/processed
    csv_dir = CSV_PROCESSED_DIR / folder_name
    excel_dir = EXCEL_PROCESSED_DIR / folder_name
    csv_dir.mkdir(parents=True, exist_ok=True)
    excel_dir.mkdir(parents=True, exist_ok=True)

    # Build descriptive filename based on search criteria
    name_parts = []
    if clean_dist:
        name_parts.append(clean_dist)
    if clean_q:
        name_parts.append(f"Query_{clean_q}")
    if clean_pin:
        name_parts.append(f"Pin_{clean_pin}")
    if not name_parts:
        name_parts.append("Maharashtra")
    if scrape_all_pages or not end_page or end_page <= 0:
        page_tag = f"{start_page}_to_All"
    else:
        page_tag = f"{start_page}_to_{end_page}"
    name_parts.append(f"Pages_{page_tag}")

    named_prefix = "_".join(name_parts)
    named_csv = csv_dir / f"{named_prefix}.csv"
    named_xlsx = excel_dir / f"{named_prefix}.xlsx"
    named_sql = csv_dir / f"{named_prefix}.sql"

    config = ScraperConfig(
        start_page=start_page,
        end_page=end_page,
        scrape_all_pages=scrape_all_pages,
        district_name=district_name,
        district_code=district_code,
        project_type_category=project_type_category,
        search_query=search_query,
        pincode=pincode,
        completion_date=completion_date,
        state=state,
        division=division,
        taluka=taluka,
        village=village,
        smart_date_check=smart_date_check,
        max_workers=max_workers,
        headless=headless,
        output_csv=str(named_csv),
        output_xlsx=str(named_xlsx),
        checkpoint_file=str(TEMP_DIR / f"checkpoint_{job_id}.json"),
        run_log_file=str(LOGS_DIR / f"run_log_{job_id}.txt"),
        failed_pages_csv=str(csv_dir / f"failed_pages_{job_id}.csv"),
        failed_projects_csv=str(csv_dir / f"failed_projects_{job_id}.csv"),
    )

    logger = ScraperLogger(log_file=config.run_log_file, callback=log_callback)
    worker = ScraperWorker(
        config=config,
        logger=logger,
        on_progress=progress_callback,
        on_record_scraped=record_scraped_callback,
        existing_projects_map=existing_projects_map,
    )

    try:
        log_callback("INFO", f"Scraper worker initialized. Pages {start_page} to {end_page} for {district_name or folder_name}")
        log_callback("INFO", f"📁 Output directories: CSV -> {csv_dir.relative_to(PROJECT_ROOT)}, Excel -> {excel_dir.relative_to(PROJECT_ROOT)}")
        log_callback("INFO", f"💾 Target files: {named_csv.name}, {named_xlsx.name}, {named_sql.name}")
        df = worker.run_scrape(page_start=start_page, page_end=end_page)

        def project_model_to_export_dict(p: Project) -> Dict[str, Any]:
            def fmt_json(v):
                if not v:
                    return ""
                if isinstance(v, dict):
                    return json.dumps(v) if v else ""
                if isinstance(v, str):
                    s = v.strip()
                    if not s or s in ("{}", "[]", "None", "nan", "null"):
                        return ""
                    return s
                return str(v)

            return {
                "Registration Number": p.registration_number or p.rera_id or "",
                "Date of Registration": p.date_of_registration.strftime("%d-%m-%Y") if p.date_of_registration else "",
                "Rera ID": p.rera_id or "",
                "Project Location": p.project_location or "",
                "Project Type": p.project_type or "",
                "Project Name": p.project_name or "",
                "survey_no": p.survey_no or "",
                "Permissible Builtup Area": p.permissible_builtup_area or "",
                "Sanctioned Builtup Area": p.sanctioned_builtup_area or "",
                "Total Land Area": p.total_land_area or "",
                "Aggregate area": getattr(p, "aggregate_area", "") or "",
                "Land Area for Project Applied for this Registration": getattr(p, "land_area_applied", "") or "",
                "Project proposed completion date original": p.project_completion_date_original.strftime("%d-%m-%Y") if p.project_completion_date_original else "",
                "Project proposed completion date revised": p.project_completion_date_revised.strftime("%d-%m-%Y") if p.project_completion_date_revised else "",
                "Longitude": p.longitude if p.longitude is not None else "",
                "Latitude": p.latitude if p.latitude is not None else "",
                "Are there any Investor other than the Promoter in the Project": p.has_investors or "",
                "State_UT": p.state_ut or "Maharashtra",
                "District": p.district or "",
                "Taluka": p.taluka or "",
                "Village": p.village or "",
                "Pin_Code": p.pin_code or "",
                "Boundaries_East": p.boundaries_east or "",
                "Boundaries_West": p.boundaries_west or "",
                "Boundaries_South": p.boundaries_south or "",
                "Boundaries_North": p.boundaries_north or "",
                "Promoter_Details": p.promoter_details or "",
                "bhk_details": fmt_json(p.bhk_details),
                "building_details": fmt_json(p.building_details),
                "Summary_of_Apartments/Units": fmt_json(p.summary_of_apartments),
                "past_experience_info": p.past_experience_info or "",
                "Litigations related to the project ?": p.litigations or "",
                "All_Parking_Details": fmt_json(p.all_parking_details),
                "Bank Name": p.bank_name or "",
                "IFSC Code": p.ifsc_code or "",
                "Bank Address": p.bank_address or "",
                "ProjectStatus": p.project_status or "",
                "Locality": p.locality or "",
                "Organization": p.organization or "",
                "Last_Modified": p.last_modified or "",
                "Commencing From": p.commencing_from or "",
                "Leftmost Date": p.leftmost_date or "",
                "Ending With": p.ending_with or "",
            }

        # If scraped df is empty or projects were skipped by smart date check,
        # assemble matching records from local database so the user always gets their data files!
        discovered_rera_ids = [
            r.get("rera_id") for r in worker.checkpoint_manager.get_project_statuses()
            if r.get("rera_id") and not str(r.get("rera_id")).startswith("UNKNOWN")
        ]

        if df is None or df.empty:
            matched_projects = []
            if discovered_rera_ids:
                matched_projects = db.query(Project).filter(Project.rera_id.in_(discovered_rera_ids)).all()
            if not matched_projects:
                q = db.query(Project)
                has_filter = False
                if search_query:
                    q = q.filter((Project.project_name.ilike(f"%{search_query}%")) | (Project.rera_id.ilike(f"%{search_query}%")))
                    has_filter = True
                if district_name and district_name.strip().lower() not in ("all", "all districts", "all / any district", ""):
                    q = q.filter(Project.district.ilike(f"%{district_name.strip()}%"))
                    has_filter = True
                if pincode:
                    q = q.filter(Project.pin_code == pincode.strip())
                    has_filter = True
                if has_filter:
                    matched_projects = q.all()

            if matched_projects:
                log_callback("INFO", f"💾 Found {len(matched_projects)} up-to-date matching record(s) in local database. Exporting to {named_prefix}.csv, .xlsx, .sql...")
                raw_records = [project_model_to_export_dict(p) for p in matched_projects]
                df_db = pd.DataFrame(raw_records)
                split_df = worker.csv_writer.split_all_large_columns(df_db, limit=config.excel_char_limit)
                final_df = split_df.reindex(columns=config.standard_columns, fill_value="")
                final_df.to_csv(named_csv, index=False, encoding="utf-8-sig")
                df = final_df

        # Ensure named_csv strictly conforms to the exact 52 standard columns
        if named_csv.exists():
            try:
                cur_df = pd.read_csv(named_csv, dtype=str)
                cur_df = cur_df.reindex(columns=config.standard_columns, fill_value="")
                cur_df.to_csv(named_csv, index=False, encoding="utf-8-sig")
                df = cur_df
            except Exception as align_err:
                log_callback("WARNING", f"Column alignment note: {align_err}")

        # Ensure district separation: split records strictly by District
        if df is not None and not df.empty:
            dist_col = "District" if "District" in df.columns else ("district" if "district" in df.columns else None)
            if dist_col and folder_name:
                target_dist_clean = folder_name.replace("_", " ").strip().lower()
                df_dist_norm = df[dist_col].fillna("Unknown").str.strip()
                unique_districts = df_dist_norm.unique()

                # If there are records belonging to other districts, partition them
                if len(unique_districts) > 1:
                    log_callback("INFO", f"🔄 Partitioning {len(df)} records strictly by District: {list(unique_districts)}")
                    for dist_val in unique_districts:
                        clean_name = dist_val.replace(" ", "_").replace("/", "_")
                        sub_df = df[df_dist_norm == dist_val]
                        if not sub_df.empty:
                            if dist_val.strip().lower() == target_dist_clean:
                                # Target district file: keep ONLY this district
                                sub_df.to_csv(named_csv, index=False, encoding="utf-8-sig")
                            else:
                                # Other district: save into its own dedicated directory and file
                                o_csv_dir = CSV_PROCESSED_DIR / clean_name
                                o_xl_dir = EXCEL_PROCESSED_DIR / clean_name
                                o_csv_dir.mkdir(parents=True, exist_ok=True)
                                o_xl_dir.mkdir(parents=True, exist_ok=True)
                                o_csv_file = o_csv_dir / f"{clean_name}_Pages_{page_tag}.csv"
                                o_xl_file = o_xl_dir / f"{clean_name}_Pages_{page_tag}.xlsx"
                                sub_df.to_csv(o_csv_file, index=False, encoding="utf-8-sig")
                                try:
                                    worker.csv_writer.export_to_xlsx(str(o_csv_file), str(o_xl_file))
                                    log_callback("INFO", f"📁 Saved {len(sub_df)} record(s) into separate district file: {o_xl_file.name}")
                                except Exception as ox_err:
                                    log_callback("WARNING", f"Excel export note for {clean_name}: {ox_err}")

                    # Reload the target district file for SQL dump and Excel export
                    if named_csv.exists():
                        df = pd.read_csv(named_csv, dtype=str)

        # Generate PostgreSQL / PL/pgSQL dump file (.sql) alongside CSV and XLSX
        if df is not None and not df.empty:
            try:
                from scraper.core.sql_exporter import generate_postgresql_dump
                generate_postgresql_dump(df.to_dict(orient="records"), named_sql, job_id=job_id)
                log_callback("INFO", f"PostgreSQL/PL-pgSQL script generated: {named_sql.name}")

                # Export Excel (.xlsx) from aligned CSV
                if named_csv.exists():
                    try:
                        worker.csv_writer.export_to_xlsx(str(named_csv), str(named_xlsx))
                    except Exception as xl_err:
                        log_callback("WARNING", f"Excel conversion note: {xl_err}")

                log_callback("INFO", f"✅ Designated output files saved: CSV -> {named_csv.name}, XLSX -> {named_xlsx.name}")
            except Exception as sql_err:
                log_callback("WARNING", f"Could not generate SQL/Excel: {sql_err}")

        # Check final status
        check_db = SessionLocal()
        final_job = check_db.query(ScrapeJob).filter(ScrapeJob.job_id == job_id).first()
        summary_stats = worker.checkpoint_manager.get_summary_stats()
        checkpoint_data = worker.checkpoint_manager.load_checkpoint()
        completed_pages = checkpoint_data.get("completed_pages", [])

        failed_pages = worker.checkpoint_manager.get_failed_pages(
            completed_pages=completed_pages,
            page_range=(start_page, end_page if not scrape_all_pages else None)
        )
        failed_projects_list = worker.checkpoint_manager.get_failed_projects()
        failed_projects_count = summary_stats.get("failed_projects", 0)

        if final_job and final_job.status != "CANCELLED":
            has_failed_pages = len(failed_pages) > 0
            has_failed_projects = (final_job.projects_failed and final_job.projects_failed > 0) or failed_projects_count > 0

            if has_failed_pages or has_failed_projects:
                final_job.status = "COMPLETED_WITH_ERRORS"
                error_reasons = []
                if has_failed_pages:
                    error_reasons.append(f"Failed to load search result page(s): {failed_pages}")
                if has_failed_projects:
                    sample_fails = [f"{fp.get('project_url', 'Unknown')}: {fp.get('reason', '')}" for fp in failed_projects_list[:2]]
                    detail_str = f" ({', '.join(sample_fails)})" if sample_fails else ""
                    error_reasons.append(f"{failed_projects_count} project(s) failed extraction{detail_str}")
                final_job.error_message = " | ".join(error_reasons)
                log_callback("WARNING", f"⚠️ Job completed with errors: {final_job.error_message}")
            else:
                final_job.status = "COMPLETED"
                final_job.error_message = None
                log_callback("SUCCESS", f"✅ Scraping completed successfully for requested scope (Pages {start_page} to {end_page or 'All'}).")

            final_job.completed_at = datetime.now()
            final_job.summary_json = summary_stats
            final_job.projects_found = max(summary_stats.get("total_discovered", 0), len(df) if df is not None else 0)
            final_job.projects_extracted = max(summary_stats.get("successful_scraped", 0), len(df) if df is not None else 0)
            final_job.projects_failed = failed_projects_count or (final_job.projects_failed or 0)
            check_db.commit()

        log_callback("INFO", f"Job finished. Summary: Discovered={summary_stats.get('total_discovered', 0)}, "
                             f"New={summary_stats.get('new_projects', 0)}, "
                             f"Skipped={summary_stats.get('unchanged_skipped', 0)}, "
                             f"Updated={summary_stats.get('updated_rescrapped', 0)}, "
                             f"Scraped={summary_stats.get('successful_scraped', 0)}, "
                             f"Failed={summary_stats.get('failed_projects', 0)}, "
                             f"Failed Pages={failed_pages}")
        check_db.close()

    except KeyboardInterrupt:
        log_callback("WARNING", "Job interrupted by user/process termination.")
        try:
            repo.update_job_status(job_id, "CANCELLED", completed_at=datetime.now())
        except Exception:
            pass
    except Exception as exc:
        full_tb = traceback.format_exc()
        log_callback("ERROR", f"Job failed with uncaught exception: {exc}")
        for tb_line in full_tb.splitlines():
            if tb_line.strip():
                log_callback("ERROR", f"  {tb_line}")
        try:
            repo.update_job_status(job_id, "FAILED", error_message=str(exc)[:250], completed_at=datetime.now())
        except Exception:
            pass
    finally:
        db.close()
        print(f"[RUNNER] Isolated scrape process for Job {job_id} terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Isolated RERA Scraper Runner")
    parser.add_argument("--job-id", required=True, help="Scrape job identifier")
    parser.add_argument("--district-name", nargs="?", const="", default="", help="Target district name")
    parser.add_argument("--district-code", nargs="?", const="", default="", help="Target district code")
    parser.add_argument("--start-page", type=int, default=1, help="Start page")
    parser.add_argument("--end-page", type=int, default=None, help="End page")
    parser.add_argument("--scrape-all-pages", action="store_true", default=False, help="Scrape all available pages")
    parser.add_argument("--max-workers", type=int, default=1, help="Max browser workers")
    parser.add_argument("--headless", action="store_true", default=False, help="Headless Chrome")
    parser.add_argument("--project-type-category", nargs="?", const="Registered Projects", default="Registered Projects", help="Project type")
    parser.add_argument("--search-query", nargs="?", const="", default="", help="Project name or RERA ID")
    parser.add_argument("--pincode", nargs="?", const="", default="", help="Pincode")
    parser.add_argument("--completion-date", nargs="?", const="", default="", help="Completion date filter")
    parser.add_argument("--state", nargs="?", const="MAHARASHTRA", default="MAHARASHTRA", help="State")
    parser.add_argument("--division", nargs="?", const="", default="", help="Division")
    parser.add_argument("--taluka", nargs="?", const="", default="", help="Taluka")
    parser.add_argument("--village", nargs="?", const="", default="", help="Village")
    parser.add_argument("--smart-date-check", action="store_true", default=False, help="Smart date check")

    args = parser.parse_args()

    run_isolated_scraper(
        job_id=args.job_id,
        district_name=args.district_name,
        district_code=args.district_code,
        start_page=args.start_page,
        end_page=args.end_page,
        max_workers=args.max_workers,
        headless=args.headless,
        project_type_category=args.project_type_category,
        search_query=args.search_query,
        pincode=args.pincode,
        completion_date=args.completion_date,
        state=args.state,
        division=args.division,
        taluka=args.taluka,
        village=args.village,
        smart_date_check=args.smart_date_check,
        scrape_all_pages=args.scrape_all_pages,
    )


if __name__ == "__main__":
    main()

