-- ====================================================================
-- RERA INSIGHT: PostgreSQL PL/pgSQL Triggers and Analytical Views
-- ====================================================================

-- 1. PL/pgSQL function to auto-update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to projects
DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
CREATE TRIGGER trg_projects_updated_at
BEFORE UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION update_timestamp_column();

-- Apply trigger to scrape_jobs
DROP TRIGGER IF EXISTS trg_scrape_jobs_updated_at ON scrape_jobs;
CREATE TRIGGER trg_scrape_jobs_updated_at
BEFORE UPDATE ON scrape_jobs
FOR EACH ROW
EXECUTE FUNCTION update_timestamp_column();

-- 2. PL/pgSQL function for automated validation of coordinates & RERA format
CREATE OR REPLACE FUNCTION validate_project_record()
RETURNS TRIGGER AS $$
DECLARE
    errors TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Check RERA ID pattern (starts with P followed by digits)
    IF NEW.rera_id !~ '^P[0-9]{5,15}$' THEN
        errors := array_append(errors, 'Invalid RERA ID format');
    END IF;

    -- Validate Maharashtra Geographic Bounding Box
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        IF NEW.latitude < 15.60 OR NEW.latitude > 22.05 OR NEW.longitude < 72.60 OR NEW.longitude > 80.90 THEN
            errors := array_append(errors, 'Coordinates outside Maharashtra bounding box');
        END IF;
    END IF;

    -- Update validation status and error list
    IF array_length(errors, 1) > 0 THEN
        NEW.validation_status := 'INVALID';
        NEW.validation_errors := to_jsonb(errors);
    ELSE
        NEW.validation_status := 'VALID';
        NEW.validation_errors := '[]'::JSONB;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_project ON projects;
CREATE TRIGGER trg_validate_project
BEFORE INSERT OR UPDATE ON projects
FOR EACH ROW
EXECUTE FUNCTION validate_project_record();

-- 3. Analytical View: District Summary
CREATE OR REPLACE VIEW view_district_summary AS
SELECT
    COALESCE(district, 'UNKNOWN') AS district,
    COUNT(*) AS total_projects,
    COUNT(CASE WHEN project_status = 'Ongoing' THEN 1 END) AS ongoing_projects,
    COUNT(CASE WHEN project_status = 'Completed' THEN 1 END) AS completed_projects,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) AS mapped_projects,
    ROUND(AVG(CASE WHEN cert_extraction_status = 'SUCCESS' THEN 100.0 ELSE 0.0 END), 1) AS cert_success_rate
FROM projects
GROUP BY district
ORDER BY total_projects DESC;

-- 4. Analytical View: Data Completeness Audit
CREATE OR REPLACE VIEW view_data_completeness AS
SELECT
    COUNT(*) AS total_records,
    COUNT(project_name) AS with_project_name,
    COUNT(district) AS with_district,
    COUNT(date_of_registration) AS with_registration_date,
    COUNT(latitude) AS with_coordinates,
    COUNT(promoter_details) AS with_promoter,
    COUNT(bank_name) AS with_bank,
    COUNT(commencing_from) AS with_cert_commencing,
    COUNT(ending_with) AS with_cert_ending
FROM projects;

