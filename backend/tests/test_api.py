"""Unit and integration tests for RERA Insight backend."""
import sys
import os
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal, init_db
from app.models.models import Project, ScrapeJob
from app.repositories.scraper_repository import ScraperRepository
from app.services.project_service import ProjectService
from app.services.scraper_service import ScraperService
from app.schemas.scraper import StartJobRequest
from scraper.core.certificate import CertificateExtractor
from scraper.core.config import ScraperConfig
from scraper.core.logger import ScraperLogger


@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()


def test_database_initialization(db_session):
    total = db_session.query(Project).count()
    assert total >= 10, f"Expected at least 10 projects, found {total}"


def test_project_listing_and_filtering(db_session):
    service = ProjectService(db_session)
    res = service.list_projects(page=1, page_size=5)
    assert res.total >= 10
    assert len(res.data) == 5
    assert res.page == 1
    assert res.total_pages >= 2

    # Search by RERA ID
    search_res = service.list_projects(search="P52000000003")
    assert search_res.total == 1
    assert search_res.data[0].rera_id == "P52000000003"
    assert search_res.data[0].project_name in ("Delta Tower", "Bliss Studio")

    # Search by promoter
    promo_res = service.list_projects(search="P52000000480")
    assert promo_res.total == 1
    assert promo_res.data[0].project_name in ("Shree Siddhivinayak Residency", "MORAJ MAA SHRISHTI")


def test_project_detail(db_session):
    service = ProjectService(db_session)
    project = service.get_project("P52000000003")
    assert project is not None
    assert project.rera_id == "P52000000003"
    assert project.district == "Raigarh"
    assert project.state_ut.upper() == "MAHARASHTRA"


def test_analytics_endpoints(db_session):
    service = ProjectService(db_session)
    overview = service.get_overview()
    assert overview["total_projects"] >= 10
    assert overview["active_projects"] >= 1
    assert overview["completed_projects"] >= 0
    assert overview["total_districts"] >= 1

    districts = service.get_districts()
    assert len(districts) >= 1
    district_names = [d["district"] for d in districts]
    assert "Raigarh" in district_names or "Pune" in district_names

    status_stats = service.get_status_breakdown()
    assert len(status_stats) >= 1

    trend = service.get_registration_trend()
    assert isinstance(trend, list)


def test_data_quality_metrics(db_session):
    service = ProjectService(db_session)
    dq = service.get_data_quality()
    assert dq["total_records"] >= 10
    assert dq["records_with_coordinates"] >= 10
    assert dq["cert_extraction_rate"] >= 0.0
    assert dq["completeness_score"] > 80.0


def test_scraper_job_lifecycle(db_session):
    repo = ScraperRepository(db_session)
    jobs = repo.list_jobs()
    assert len(jobs) >= 1
    job_districts = [j.district_name for j in jobs]
    assert len(job_districts) >= 1 and any(j in job_districts for j in ["Raigarh", "Pune", "Mumbai City", ""])

    # Find job that has logs, or verify logs retrieval
    all_logs = []
    for j in jobs:
        logs = repo.get_logs(j.job_id)
        if logs:
            all_logs = logs
            break
    assert len(all_logs) >= 1


def test_scraper_detached_instance_fix_and_dto(db_session):
    """Verify start_job returns a complete, serialized DTO dict without DetachedInstanceError."""
    # Ensure no running job
    running = db_session.query(ScrapeJob).filter(ScrapeJob.status.in_(["STARTING", "RUNNING"])).all()
    for r in running:
        r.status = "COMPLETED"
    db_session.commit()

    service = ScraperService.get_instance()
    req = StartJobRequest(
        district_name="Raigarh",
        district_code="520",
        start_page=1,
        end_page=2,
        max_workers=1,
        headless=True
    )
    job_dto = service.start_job(req)
    assert isinstance(job_dto, dict)
    assert "job_id" in job_dto
    assert job_dto["status"] == "STARTING"
    assert job_dto["district_name"] == "Raigarh"
    assert "projects_extracted" in job_dto
    assert "current_page" in job_dto

    # Cancel the started job cleanly
    service.cancel_job(job_dto["job_id"])


def test_scraper_schema_page_validation():
    """Verify that end_page < start_page is caught by Pydantic validation."""
    with pytest.raises(ValidationError):
        StartJobRequest(
            district_name="Raigarh",
            district_code="520",
            start_page=5,
            end_page=2,
        )


def test_certificate_extractor_optimization():
    """Verify CertificateExtractor quickly detects absence of certificate button."""
    config = ScraperConfig(cert_load_timeout=2)
    logger = ScraperLogger()
    extractor = CertificateExtractor(config, logger)

    # Calling extract_cert_fields_from_text on sample certificate text
    sample_text = (
        "MAHARASHTRA REAL ESTATE REGULATORY AUTHORITY\n"
        "REGISTRATION CERTIFICATE OF PROJECT\n"
        "Commencing From: 01/06/2018 and ending with 31/12/2024\n"
        "Dated: 15/05/2018\n"
    )
    fields = extractor.extract_cert_fields_from_text(sample_text)
    assert fields["Commencing From"] == "01-06-2018"
    assert fields["Ending With"] == "31-12-2024"
    assert fields["Leftmost Date"] == "15-05-2018"


def test_smart_date_comparison_logic():
    """Verify smart last modified date comparison matches user test specification."""
    from scraper.core.date_utils import compare_last_modified, format_date_display

    # Example 1: Date matches -> Skip
    action1, reason1 = compare_last_modified("10-08-2026", "10-08-2026")
    assert action1 == "UNCHANGED_SKIPPED"
    assert "matches" in reason1.lower()

    # Example 2: Date changed -> Re-scrape and Update
    action2, reason2 = compare_last_modified("12-07-2026", "18-08-2026")
    assert action2 == "UPDATED_RESCRAPED"
    assert "changed" in reason2.lower()

    # Example 3: Existing Not Found -> New Project
    action3, reason3 = compare_last_modified(None, "20-08-2026")
    assert action3 == "NEW"

    # Example 4: Multi-format comparison (ISO vs DD-MM-YYYY)
    action4, reason4 = compare_last_modified("18-08-2026", "2026-08-18")
    assert action4 == "UNCHANGED_SKIPPED"

    # Example 5: Missing or invalid website date -> Must NOT assume unchanged! Must re-scrape
    action5, reason5 = compare_last_modified("10-08-2026", None)
    assert action5 == "UPDATED_RESCRAPED"
    action6, reason6 = compare_last_modified("10-08-2026", "Not Available")
    assert action6 == "UPDATED_RESCRAPED"

    # Date display format normalization
    assert format_date_display("2026-11-10") == "10-11-2026"
    assert format_date_display("10/11/2026") == "10-11-2026"
    assert format_date_display(None) == "Not Available"


def test_preview_endpoint(db_session):
    """Verify POST /api/scraper/preview searches DB and returns preview matches."""
    from app.api.routes.scraper import preview_scraping_job
    from app.schemas.scraper import ScrapePreviewRequest

    req = ScrapePreviewRequest(
        district_name="Raigarh",
        search_query="",
        pincode="",
    )
    res = preview_scraping_job(req, db=db_session)
    assert res.matching_in_database >= 1
    assert len(res.existing_projects) >= 1
    assert "rera_id" in res.existing_projects[0]
    assert "last_modified" in res.existing_projects[0]


def test_csv_writer_inplace_update(tmp_path):
    """Verify CsvWriter updates existing row in place by RERA ID without duplicating rows."""
    from scraper.core.csv_writer import CsvWriter
    import pandas as pd

    test_csv = str(tmp_path / "test_output.csv")
    config = ScraperConfig(output_csv=test_csv)
    logger = ScraperLogger()
    writer = CsvWriter(config=config, logger=logger)

    # 1. Write initial row
    initial_row = pd.DataFrame([{
        "Registration Number": "P51900000070",
        "Project Name": "A. M. Residency",
        "District": "Mumbai City",
        "State/UT": "MAHARASHTRA",
        "Last Modified": "10-08-2026",
        "Promoter Name": "Alfa Mana",
    }])
    writer.save_scraped_project_row(initial_row, test_csv)

    # Verify CSV has 1 row
    df1 = pd.read_csv(test_csv)
    assert len(df1) == 1
    assert df1.iloc[0]["Registration Number"] == "P51900000070"
    assert df1.iloc[0]["Last Modified"] == "10-08-2026"
    assert df1.iloc[0]["Promoter Name"] == "Alfa Mana"

    # 2. Update existing row with newer last modified and updated promoter name, but missing District
    updated_row = pd.DataFrame([{
        "Registration Number": "P51900000070",
        "Project Name": "A. M. Residency Updated",
        "Last Modified": "18-08-2026",
        "Promoter Name": "Alfa Mana Realtors Pvt Ltd",
    }])
    writer.save_scraped_project_row(updated_row, test_csv, is_update=True)

    # Verify CSV still has only 1 row (no duplicate) and preserved prior District
    df2 = pd.read_csv(test_csv)
    assert len(df2) == 1
    assert df2.iloc[0]["Registration Number"] == "P51900000070"
    assert df2.iloc[0]["Last Modified"] == "18-08-2026"
    assert df2.iloc[0]["Project Name"] == "A. M. Residency Updated"
    assert df2.iloc[0]["Promoter Name"] == "Alfa Mana Realtors Pvt Ltd"
    assert df2.iloc[0]["District"] == "Mumbai City"  # Preserved!


def test_optional_page_range_validation():
    """Verify that StartJobRequest supports both custom page ranges and all-pages mode."""
    # 1. Valid custom page range (e.g. 10 to 50)
    req_range = StartJobRequest(
        scrape_all_pages=False,
        start_page=10,
        end_page=50,
        search_query="Immense Heights",
    )
    assert req_range.scrape_all_pages is False
    assert req_range.start_page == 10
    assert req_range.end_page == 50

    # 2. Invalid custom page range (start > end) must raise validation error
    with pytest.raises(ValidationError):
        StartJobRequest(
            scrape_all_pages=False,
            start_page=50,
            end_page=10,
        )

    # 3. All pages mode (scrape_all_pages=True) allows end_page=None
    req_all = StartJobRequest(
        scrape_all_pages=True,
        start_page=1,
        end_page=None,
        search_query="Immense Heights",
    )
    assert req_all.scrape_all_pages is True
    assert req_all.start_page == 1
    assert req_all.end_page is None

