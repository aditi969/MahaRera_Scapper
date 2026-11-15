export interface ProjectListItem {
  rera_id: string;
  registration_number?: string | null;
  date_of_registration?: string | null;
  project_name?: string | null;
  project_type?: string | null;
  project_status?: string | null;
  district?: string | null;
  taluka?: string | null;
  village?: string | null;
  locality?: string | null;
  organization?: string | null;
  promoter_details?: string | null;
  project_completion_date_original?: string | null;
  project_completion_date_revised?: string | null;
  validation_status?: string | null;
  created_at?: string | null;
}

export interface ProjectListResponse {
  data: ProjectListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProjectDetail {
  rera_id: string;
  registration_number?: string | null;
  date_of_registration?: string | null;
  project_name?: string | null;
  project_location?: string | null;
  project_type?: string | null;
  project_status?: string | null;
  district?: string | null;
  taluka?: string | null;
  village?: string | null;
  state_ut?: string | null;
  locality?: string | null;
  pin_code?: string | null;
  longitude?: number | null;
  latitude?: number | null;
  survey_no?: string | null;
  total_land_area?: string | null;
  permissible_builtup_area?: string | null;
  sanctioned_builtup_area?: string | null;
  project_completion_date_original?: string | null;
  project_completion_date_revised?: string | null;
  boundaries_east?: string | null;
  boundaries_west?: string | null;
  boundaries_south?: string | null;
  boundaries_north?: string | null;
  promoter_details?: string | null;
  has_investors?: string | null;
  past_experience_info?: string | null;
  litigations?: string | null;
  bank_name?: string | null;
  ifsc_code?: string | null;
  bank_address?: string | null;
  bhk_details?: Record<string, any> | null;
  building_details?: Record<string, any> | null;
  summary_of_apartments?: Record<string, any> | null;
  all_parking_details?: Record<string, any> | null;
  organization?: string | null;
  last_modified?: string | null;
  commencing_from?: string | null;
  leftmost_date?: string | null;
  ending_with?: string | null;
  cert_date_source?: string | null;
  source_url?: string | null;
  scrape_job_id?: string | null;
  is_duplicate: boolean;
  validation_status?: string | null;
  validation_errors?: string[] | null;
  extraction_errors?: Record<string, any> | null;
  cert_extraction_status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  scraped_at?: string | null;
}

export interface MapProject {
  rera_id: string;
  project_name?: string | null;
  project_status?: string | null;
  district?: string | null;
  project_type?: string | null;
  latitude: number;
  longitude: number;
  promoter_details?: string | null;
}

export interface OverviewKPIs {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  total_districts: number;
  latest_scrape_date?: string | null;
}

export interface DistrictStat {
  district: string;
  count: number;
}

export interface StatusStat {
  status: string;
  count: number;
}

export interface ProjectTypeStat {
  project_type: string;
  count: number;
}

export interface TrendPoint {
  period: string;
  count: number;
}

export interface CompletionPoint {
  year: string;
  count: number;
}

export interface DataQualityMetrics {
  total_records: number;
  valid_rera_ids: number;
  records_with_coordinates: number;
  records_missing_district: number;
  records_missing_completion_date: number;
  records_with_cert_dates: number;
  cert_extraction_rate: number;
  duplicate_count: number;
  validation_pass_count: number;
  validation_fail_count: number;
  completeness_score: number;
  by_extraction_status: { status: string; count: number }[];
}

export interface ScrapeJobItem {
  job_id: string;
  district_name: string;
  district_code: string;
  start_page: number;
  end_page: number;
  headless: boolean;
  max_workers: number;
  status: string;
  projects_found: number;
  projects_extracted: number;
  projects_failed: number;
  current_page?: number;
  certificates_extracted?: number;
  certificates_failed?: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScrapeLogItem {
  id: number;
  job_id: string;
  level: string;
  message: string;
  extra?: Record<string, any> | null;
  created_at: string;
}

export interface StartScrapeRequest {
  district_name: string;
  district_code: string;
  start_page: number;
  end_page: number;
  headless: boolean;
  max_workers: number;
}
