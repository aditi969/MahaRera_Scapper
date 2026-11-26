-- ====================================================================
-- RERA INSIGHT: PostgreSQL Production Schema
-- Tables: projects, scrape_jobs, scrape_logs, data_quality_checks
-- ====================================================================

-- 1. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    rera_id VARCHAR(32) PRIMARY KEY,
    registration_number VARCHAR(64),
    date_of_registration DATE,
    project_name VARCHAR(255),
    project_location TEXT,
    project_type VARCHAR(64),
    project_status VARCHAR(64),
    district VARCHAR(64),
    taluka VARCHAR(64),
    village VARCHAR(128),
    state_ut VARCHAR(64) DEFAULT 'MAHARASHTRA',
    locality VARCHAR(255),
    pin_code VARCHAR(16),
    longitude NUMERIC(10, 6),
    latitude NUMERIC(10, 6),
    survey_no VARCHAR(255),
    total_land_area VARCHAR(64),
    permissible_builtup_area VARCHAR(64),
    sanctioned_builtup_area VARCHAR(64),
    project_completion_date_original DATE,
    project_completion_date_revised DATE,
    boundaries_east TEXT,
    boundaries_west TEXT,
    boundaries_south TEXT,
    boundaries_north TEXT,
    promoter_details TEXT,
    has_investors VARCHAR(16),
    past_experience_info TEXT,
    litigations TEXT,
    bank_name VARCHAR(128),
    ifsc_code VARCHAR(32),
    bank_address TEXT,
    bhk_details JSONB,
    building_details JSONB,
    summary_of_apartments JSONB,
    all_parking_details JSONB,
    organization VARCHAR(128),
    last_modified VARCHAR(64),
    commencing_from DATE,
    leftmost_date DATE,
    ending_with DATE,
    cert_date_source VARCHAR(64),
    source_url TEXT,
    scrape_job_id VARCHAR(64),
    is_duplicate BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(32) DEFAULT 'VALID',
    validation_errors JSONB,
    extraction_errors JSONB,
    cert_extraction_status VARCHAR(32) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Scrape Jobs Table
CREATE TABLE IF NOT EXISTS scrape_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    district_name VARCHAR(64) NOT NULL,
    district_code VARCHAR(16) NOT NULL,
    start_page INTEGER NOT NULL DEFAULT 1,
    end_page INTEGER NOT NULL DEFAULT 1,
    headless BOOLEAN NOT NULL DEFAULT TRUE,
    max_workers INTEGER NOT NULL DEFAULT 2,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    projects_found INTEGER DEFAULT 0,
    projects_extracted INTEGER DEFAULT 0,
    projects_failed INTEGER DEFAULT 0,
    current_page INTEGER DEFAULT 1,
    certificates_extracted INTEGER DEFAULT 0,
    certificates_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Scrape Logs Table
CREATE TABLE IF NOT EXISTS scrape_logs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(64) REFERENCES scrape_jobs(job_id) ON DELETE CASCADE,
    level VARCHAR(16) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    extra JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Data Quality Checks Table
CREATE TABLE IF NOT EXISTS data_quality_checks (
    id SERIAL PRIMARY KEY,
    check_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    total_evaluated INTEGER NOT NULL DEFAULT 0,
    failures_count INTEGER NOT NULL DEFAULT 0,
    pass_rate NUMERIC(5, 2) NOT NULL DEFAULT 100.0,
    details JSONB,
    run_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast query performance
CREATE INDEX IF NOT EXISTS idx_projects_district ON projects(district);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(project_status);
CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(project_type);
CREATE INDEX IF NOT EXISTS idx_projects_coords ON projects(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_projects_completion ON projects(project_completion_date_revised, project_completion_date_original);
CREATE INDEX IF NOT EXISTS idx_projects_job_id ON projects(scrape_job_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_job_id ON scrape_logs(job_id);

