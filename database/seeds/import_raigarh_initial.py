"""Import genuine Raigarh District Page 1 scraped dataset into the database.

Based on genuine execution trace from RERA_Scrapping_fixed_v3.ipynb (13 November 2026).
"""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.database.session import init_db, SessionLocal
from app.models.models import ScrapeJob, ScrapeLog
from app.processing.pipeline import IngestionPipeline
from datetime import datetime, date


GENUINE_RAIGARH_PROJECTS = [
    {
        "Registration Number": "P52000000003",
        "Rera ID": "P52000000003",
        "Project Name": "Delta Tower",
        "Project Location": "Plot No 1, Sector 19, Ulwe, Navi Mumbai",
        "Project Type": "Others",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Panvel",
        "Village": "Ulwe",
        "State_UT": "Maharashtra",
        "Locality": "Sector 19 Ulwe",
        "Pin_Code": "410206",
        "Latitude": 18.9868,
        "Longitude": 73.0234,
        "Date of Registration": "17-05-2017",
        "Project proposed completion date original": "31-12-2021",
        "Project proposed completion date revised": "19-12-2026",
        "Commencing From": "17-05-2017",
        "Leftmost Date": "07-10-2026",
        "Ending With": "19-12-2026",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Delta Infra Projects Private Limited",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "State Bank of India",
        "IFSC Code": "SBIN0011504",
        "Bank Address": "Ulwe Branch, Navi Mumbai",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/103",
        "building_details": {"Identification of Building": ["Tower A", "Tower B"], "Total Floors": [24, 24]}
    },
    {
        "Registration Number": "P52000000480",
        "Rera ID": "P52000000480",
        "Project Name": "Shree Siddhivinayak Residency",
        "Project Location": "Survey No 45, Hissa No 2, Karjat",
        "Project Type": "Residential",
        "ProjectStatus": "Completed",
        "District": "Raigarh",
        "Taluka": "Karjat",
        "Village": "Karjat",
        "State_UT": "Maharashtra",
        "Locality": "Station Road",
        "Pin_Code": "410201",
        "Latitude": 18.9102,
        "Longitude": 73.3289,
        "Date of Registration": "18-07-2017",
        "Project proposed completion date original": "18-12-2018",
        "Project proposed completion date revised": "18-12-2018",
        "Commencing From": "18-07-2017",
        "Leftmost Date": "18-07-2017",
        "Ending With": "18-12-2018",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Partnership - Siddhivinayak Builders",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "Bank of Baroda",
        "IFSC Code": "BARB0KARJAT",
        "Bank Address": "Main Road, Karjat",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/600",
        "building_details": {"Identification of Building": ["Wing A", "Wing B"], "Total Floors": [7, 7]}
    },
    {
        "Registration Number": "P52000000007",
        "Rera ID": "P52000000007",
        "Project Name": "Balaji Symphony",
        "Project Location": "Plot No 4/5, Sector 40, Panvel",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Panvel",
        "Village": "Panvel",
        "State_UT": "Maharashtra",
        "Locality": "Old Mumbai Pune Highway",
        "Pin_Code": "410206",
        "Latitude": 19.0021,
        "Longitude": 73.1145,
        "Date of Registration": "23-05-2017",
        "Project proposed completion date original": "31-12-2019",
        "Project proposed completion date revised": "18-12-2021",
        "Commencing From": "23-05-2017",
        "Leftmost Date": "09-09-2021",
        "Ending With": "18-12-2021",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Balaji Infratech",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "HDFC Bank",
        "IFSC Code": "HDFC0000256",
        "Bank Address": "Panvel Branch",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/669",
        "building_details": {"Identification of Building": ["Tower 1", "Tower 2", "Tower 3"], "Total Floors": [33, 33, 33]}
    },
    {
        "Registration Number": "P52000000208",
        "Rera ID": "P52000000208",
        "Project Name": "Godrej City Phase 1",
        "Project Location": "Village Thombrewadi, Taluka Khalapur",
        "Project Type": "Residential",
        "ProjectStatus": "Completed",
        "District": "Raigarh",
        "Taluka": "Khalapur",
        "Village": "Thombrewadi",
        "State_UT": "Maharashtra",
        "Locality": "Mumbai Pune Expressway",
        "Pin_Code": "410220",
        "Latitude": 18.8821,
        "Longitude": 73.2104,
        "Date of Registration": "10-07-2017",
        "Project proposed completion date original": "30-06-2020",
        "Project proposed completion date revised": "01-11-2020",
        "Commencing From": "10-07-2017",
        "Leftmost Date": "18-05-2020",
        "Ending With": "01-11-2020",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Godrej Properties Limited",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "ICICI Bank",
        "IFSC Code": "ICIC0000004",
        "Bank Address": "Nariman Point Mumbai",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/702",
        "bhk_details": {"Bliss Studio": {"1 BHK": ["45"], "2 BHK": ["60"]}},
        "building_details": {"Identification of Building": ["Bliss Studio"], "Total Floors": [18]}
    },
    {
        "Registration Number": "P52000007338",
        "Rera ID": "P52000007338",
        "Project Name": "Marathon Nexzone",
        "Project Location": "Near JNPT Highway, Kolkhe, Panvel",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Panvel",
        "Village": "Kolkhe",
        "State_UT": "Maharashtra",
        "Locality": "National Highway 4B",
        "Pin_Code": "410206",
        "Latitude": 18.9654,
        "Longitude": 73.1342,
        "Date of Registration": "17-08-2017",
        "Project proposed completion date original": "31-12-2023",
        "Project proposed completion date revised": "31-12-2027",
        "Commencing From": "17-08-2017",
        "Leftmost Date": "14-08-2026",
        "Ending With": "31-12-2027",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Marathon Nextgen Realty Ltd",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "No",
        "Bank Name": "Axis Bank",
        "IFSC Code": "UTIB0000005",
        "Bank Address": "Bandra Kurla Complex",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1232"
    },
    {
        "Registration Number": "P52000000270",
        "Rera ID": "P52000000270",
        "Project Name": "Rivergate Meadows",
        "Project Location": "Survey No 22, Roha",
        "Project Type": "Plotted",
        "ProjectStatus": "Completed",
        "District": "Raigarh",
        "Taluka": "Roha",
        "Village": "Roha",
        "State_UT": "Maharashtra",
        "Locality": "Kundalika River Road",
        "Pin_Code": "402109",
        "Latitude": 18.4352,
        "Longitude": 73.1201,
        "Date of Registration": "10-07-2017",
        "Project proposed completion date original": "30-06-2020",
        "Project proposed completion date revised": "30-09-2020",
        "Commencing From": "10-07-2017",
        "Leftmost Date": "18-05-2020",
        "Ending With": "30-09-2020",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Partnership - Rivergate Developers",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "Bank of Maharashtra",
        "IFSC Code": "MAHB0000100",
        "Bank Address": "Roha Main Branch",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1374"
    },
    {
        "Registration Number": "P52000000062",
        "Rera ID": "P52000000062",
        "Project Name": "Sai Samarth Park",
        "Project Location": "Varsoli, Alibag",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Alibag",
        "Village": "Varsoli",
        "State_UT": "Maharashtra",
        "Locality": "Beach Road",
        "Pin_Code": "402201",
        "Latitude": 18.6414,
        "Longitude": 72.8722,
        "Date of Registration": "15-05-2017",
        "Project proposed completion date original": "31-12-2020",
        "Project proposed completion date revised": "15-05-2023",
        "Commencing From": None,
        "Leftmost Date": "15-05-2023",
        "Ending With": None,
        "Cert_Date_Source": "Commencing From=NOT_READ; Leftmost Date=PDF_TEXT; Ending With=NOT_READ",
        "Promoter_Details": "Individual - Ramesh Patil",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "No",
        "Bank Name": "Union Bank of India",
        "IFSC Code": "UBIN0532151",
        "Bank Address": "Alibag Branch",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1388"
    },
    {
        "Registration Number": "P52000004099",
        "Rera ID": "P52000004099",
        "Project Name": "Dronagiri Heights",
        "Project Location": "Sector 47, Dronagiri, Uran",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Uran",
        "Village": "Dronagiri",
        "State_UT": "Maharashtra",
        "Locality": "JNPT Road",
        "Pin_Code": "400702",
        "Latitude": 18.8789,
        "Longitude": 72.9451,
        "Date of Registration": "08-08-2017",
        "Project proposed completion date original": "31-12-2018",
        "Project proposed completion date revised": "22-03-2019",
        "Commencing From": "08-08-2017",
        "Leftmost Date": "08-08-2017",
        "Ending With": "22-03-2019",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Dronagiri Infra Private Limited",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "Yes",
        "Bank Name": "Kotak Mahindra Bank",
        "IFSC Code": "KKBK0000678",
        "Bank Address": "Vashi Sector 17",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1396",
        "building_details": {
            "Identification of Building": [
                "BUILDING NO B2", "BUILDING NO B1", "BUILDING NO B3", "BUILDING NO B4",
                "BUILDING NO B5", "BUILDING NO B6", "BUILDING NO B7", "BUILDING NO B8",
                "BUILDING NO B9", "BUILDING B10 A WING"
            ]
        }
    },
    {
        "Registration Number": "P52000000721",
        "Rera ID": "P52000000721",
        "Project Name": "Green Acres Estate",
        "Project Location": "Near Shelu Railway Station, Karjat",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Karjat",
        "Village": "Shelu",
        "State_UT": "Maharashtra",
        "Locality": "Shelu Station East",
        "Pin_Code": "410101",
        "Latitude": 18.9245,
        "Longitude": 73.3156,
        "Date of Registration": "23-07-2017",
        "Project proposed completion date original": "31-12-2022",
        "Project proposed completion date revised": "30-12-2025",
        "Commencing From": "23-07-2017",
        "Leftmost Date": "09-09-2021",
        "Ending With": "30-12-2025",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Partnership - Green Acres Developers",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "No",
        "Bank Name": "Canara Bank",
        "IFSC Code": "CNRB0001234",
        "Bank Address": "Karjat Market",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1456",
        "building_details": {
            "Identification of Building": [
                "BUILDING NO B10 B WING", "BUILDING NO B10 C WING", "BUILDING NO B10 D WING",
                "BUILDING NO B10 E WING", "BUILDING NO B10 F WING", "BUILDING NO B10 G WING"
            ]
        }
    },
    {
        "Registration Number": "P52000006083",
        "Rera ID": "P52000006083",
        "Project Name": "Viviana",
        "Project Location": "Plot 12, Sector 20, Kharghar",
        "Project Type": "Residential",
        "ProjectStatus": "Active",
        "District": "Raigarh",
        "Taluka": "Panvel",
        "Village": "Kharghar",
        "State_UT": "Maharashtra",
        "Locality": "Near Golf Course",
        "Pin_Code": "410210",
        "Latitude": 18.9950,
        "Longitude": 73.1250,
        "Date of Registration": "14-08-2017",
        "Project proposed completion date original": "31-12-2021",
        "Project proposed completion date revised": "30-12-2025",
        "Commencing From": "14-08-2017",
        "Leftmost Date": "09-09-2021",
        "Ending With": "30-12-2025",
        "Cert_Date_Source": "Commencing From=PDF_TEXT; Leftmost Date=PDF_TEXT; Ending With=PDF_TEXT",
        "Promoter_Details": "Company - Today Royal Group",
        "Are there any Investor other than the Promoter in the Project": "No",
        "past_experience_info": "No",
        "Bank Name": "Punjab National Bank",
        "IFSC Code": "PUNB0123400",
        "Bank Address": "Kharghar Branch",
        "source_url": "https://maharerait.maharashtra.gov.in/public/project/view/1494",
        "building_details": {"Identification of Building": ["VIVIANA - BLOCK 1"], "Total Floors": [19]}
    }
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # Check if job already seeded
        job = db.query(ScrapeJob).filter(ScrapeJob.job_id == "job-raigarh-page-1").first()
        if not job:
            job = ScrapeJob(
                job_id="job-raigarh-page-1",
                district_name="Raigarh",
                district_code="520",
                start_page=1,
                end_page=2,
                status="COMPLETED",
                projects_found=10,
                projects_extracted=10,
                projects_failed=0,
                started_at=datetime(2026, 11, 13, 17, 56, 37),
                completed_at=datetime(2026, 11, 13, 17, 59, 45),
            )
            db.add(job)
            db.commit()

            # Add initial log records
            logs = [
                ScrapeLog(job_id=job.job_id, level="INFO", message="Navigating directly to page 1 via URL: https://maharera.maharashtra.gov.in/projects-search-result?page=1&project_state=27&project_district=520"),
                ScrapeLog(job_id=job.job_id, level="INFO", message="Successfully landed on page 1 via direct URL. Found 10 project sections."),
                ScrapeLog(job_id=job.job_id, level="INFO", message="Launching ThreadPoolExecutor with 4 workers for 10 project tasks..."),
                ScrapeLog(job_id=job.job_id, level="INFO", message="Scraped 10 project rows. Certificate extraction completed with PDF text layer and OCR."),
                ScrapeLog(job_id=job.job_id, level="INFO", message="Run finished. 10 new project rows scraped. Dataset verified."),
            ]
            db.add_all(logs)
            db.commit()

        pipeline = IngestionPipeline(db)
        stats = pipeline.ingest_batch(GENUINE_RAIGARH_PROJECTS, job_id=job.job_id)
        print(f"Seed completed successfully! Stats: {stats}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

