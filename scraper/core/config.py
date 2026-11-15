"""Configuration and tunable parameters for the MahaRERA scraper.

Matches exact settings from Cell 1 of RERA_Scrapping_fixed_v3.ipynb.
"""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class ScraperConfig:
    tesseract_path: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    start_page: int = 1
    end_page: int = 2  # exclusive

    max_workers: int = 1  # Default to 1 isolated browser worker for stability (max 2)

    district_name: str = "Raigarh"
    pincode: str = ""

    # URL-based pagination params
    project_state: str = "27"  # Maharashtra state code
    district_code: str = "520"  # Raigarh district code

    base_search_url: str = "https://maharera.maharashtra.gov.in/projects-search-result"

    output_csv: str = "Raigarh_output_NEW.csv"
    checkpoint_file: str = "checkpoint.json"
    failed_pages_csv: str = "failed_pages.csv"
    failed_projects_csv: str = "failed_projects.csv"
    run_log_file: str = "run_log.txt"

    excel_char_limit: int = 32000
    output_xlsx: str = "Raigarh_output_NEW.xlsx"
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
        "Commencing From", "Leftmost Date", "Ending With", "Cert_Date_Source"
    ])

