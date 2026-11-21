"""Configuration and tunable parameters for the MahaRERA scraper.

Matches exact settings from Cell 1 of RERA_Scrapping_fixed_v3.ipynb.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional


from scraper.core.storage import CSV_PROCESSED_DIR, EXCEL_PROCESSED_DIR, TEMP_DIR, LOGS_DIR, ensure_all_storage_dirs
ensure_all_storage_dirs()

@dataclass
class ScraperConfig:
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    start_page: int = 1
    end_page: Optional[int] = 2  # When None or 0, or scrape_all_pages=True, scrape until last page
    scrape_all_pages: bool = False  # When True, scrape all available pages automatically

    max_workers: int = 1  # Default to 1 isolated browser worker for stability (max 2)

    district_name: str = "Raigarh"
    pincode: str = ""

    # Search Filters from MahaRERA website
    project_type_category: str = "Registered Projects"  # "Registered Projects" or "Revoked Projects"
    search_query: str = ""                              # Project Name or MahaRERA Registration Number
    completion_date: str = ""                           # Project completion date filter
    division: str = ""                                  # Division filter
    taluka: str = ""                                    # Taluka filter
    village: str = ""                                   # Village filter
    locality: str = ""                                  # Locality filter

    # Smart Last Modified Date checking
    smart_date_check: bool = True

    # State and District parameters
    state: str = "MAHARASHTRA"
    project_state: str = "27"  # Maharashtra state code
    district_code: str = ""    # District code

    base_search_url: str = "https://maharera.maharashtra.gov.in/projects-search-result"

    output_csv: str = field(default_factory=lambda: str(CSV_PROCESSED_DIR / "Raigarh_output_NEW.csv"))
    checkpoint_file: str = field(default_factory=lambda: str(TEMP_DIR / "checkpoint.json"))
    failed_pages_csv: str = field(default_factory=lambda: str(CSV_PROCESSED_DIR / "failed_pages.csv"))
    failed_projects_csv: str = field(default_factory=lambda: str(CSV_PROCESSED_DIR / "failed_projects.csv"))
    run_log_file: str = field(default_factory=lambda: str(LOGS_DIR / "run_log.txt"))

    excel_char_limit: int = 32000
    output_xlsx: str = field(default_factory=lambda: str(EXCEL_PROCESSED_DIR / "Raigarh_output_NEW.xlsx"))
    auto_export_excel: bool = True

    max_captcha_ocr_attempts: int = 3
    cert_load_timeout: int = 12
    cert_max_retries: int = 3
    cert_full_retries: int = 2
    refresh_attempts: int = 1
    max_page_retries: int = 2
    max_project_retries: int = 2
    page_load_wait: int = 2
    retry_backoff_seconds: int = 2

    refresh_page_on_nav_fail: bool = True
    page_refresh_attempts: int = 2
    restart_driver_on_consecutive_failures: int = 2

    skip_failed_pages: bool = True
    skip_failed_projects: bool = True
    auto_retry_failed_at_end: bool = True

    headless: bool = True

    standard_columns: List[str] = field(default_factory=lambda: [
        "Registration Number", "Date of Registration", "Rera ID", "Project Location",
        "Project Type", "Project Name", "survey_no",
        "Permissible Builtup Area", "Sanctioned Builtup Area", "Total Land Area",
        "Aggregate area", "Land Area for Project Applied for this Registration",
        "Project proposed completion date original", "Project proposed completion date revised",
        "Longitude", "Latitude", "Are there any Investor other than the Promoter in the Project",
        "State_UT", "District", "Taluka", "Village", "Pin_Code",
        "Boundaries_East", "Boundaries_West", "Boundaries_South",
        "Boundaries_North", "Boundaries_North_part2",
        "Promoter_Details", "Promoter_Details_part2", "Promoter_Details_part3", "Promoter_Details_part4", "Promoter_Details_part5",
        "bhk_details", "bhk_details_part2", "bhk_details_part3", "bhk_details_part4", "bhk_details_part5",
        "building_details", "Summary_of_Apartments/Units",
        "past_experience_info", "Litigations related to the project ?",
        "All_Parking_Details", "Bank Name", "IFSC Code", "Bank Address", "ProjectStatus",
        "Locality", "Organization", "Last_Modified",
        "Commencing From", "Leftmost Date", "Ending With"
    ])

