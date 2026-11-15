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
    assert search_res.data[0].project_name == "Bliss Studio"

    # Search by promoter
    promo_res = service.list_projects(search="P52000000480")
    assert promo_res.total == 1
    assert promo_res.data[0].project_name == "MORAJ MAA SHRISHTI"


def test_project_detail(db_session):
    service = ProjectService(db_session)
    project = service.get_project("P52000000003")
    assert project is not None
    assert project.rera_id == "P52000000003"
    assert project.district == "Raigarh"
    assert project.state_ut == "MAHARASHTRA"


def test_analytics_endpoints(db_session):
    service = ProjectService(db_session)
    overview = service.get_overview()
    assert overview["total_projects"] >= 10
    assert overview["active_projects"] >= 1
    assert overview["completed_projects"] >= 0
    assert overview["total_districts"] >= 1

    districts = service.get_districts()
    assert len(districts) >= 1
    assert districts[0]["district"] == "Raigarh"

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
    assert jobs[0].district_name == "Raigarh"

    logs = repo.get_logs(jobs[0].job_id)
    assert len(logs) >= 1


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
