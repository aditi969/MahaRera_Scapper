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

export interface ScrapeJobSummary {
  total_discovered?: number;
  new_projects?: number;
  new_projects_found?: number;
  existing_checked?: number;
  unchanged_skipped?: number;
  updated_rescrapped?: number;
  updated_rescraped?: number;
  successful_scraped?: number;
  successfully_scraped?: number;
  failed_projects?: number;
  total_saved_or_updated?: number;
  project_records?: any[];
  export_files?: Record<string, any>;
  project_details?: Record<string, {
    rera_id?: string;
    project_name?: string;
    status: string;
    website_last_modified?: string;
    stored_last_modified?: string;
    timestamp?: number;
    error?: string;
  }>;
}

export interface ScrapeJobItem {
  job_id: string;
  district_name: string;
  district_code: string;
  start_page: number;
  end_page?: number | null;
  headless: boolean;
  max_workers: number;
  status: string;
  projects_found: number;
  projects_extracted: number;
  projects_failed: number;
  current_page?: number;
  certificates_extracted?: number;
  certificates_failed?: number;
  filters_json?: Record<string, any> | null;
  summary_json?: ScrapeJobSummary | null;
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
  district_name?: string;
  district_code?: string;
  start_page?: number;
  end_page?: number | null;
  scrape_all_pages?: boolean;
  headless: boolean;
  max_workers: number;
  project_type_category?: string;
  search_query?: string;
  pincode?: string;
  completion_date?: string;
  state?: string;
  division?: string;
  taluka?: string;
  village?: string;
  smart_date_check?: boolean;
}

export interface ScrapePreviewRequest {
  district_name?: string;
  search_query?: string;
  pincode?: string;
  completion_date?: string;
  project_type_category?: string;
}

export interface ScrapePreviewRecord {
  rera_id: string;
  project_name?: string;
  district?: string;
  pincode?: string;
  last_modified?: string;
  proposed_completion_date?: string;
  status?: string;
}

export interface ScrapePreviewResponse {
  matching_in_database: number;
  existing_projects: ScrapePreviewRecord[];
  sample_records: ScrapePreviewRecord[];
  filters_applied: Record<string, any>;
}

export interface ScrapedProjectItem {
  rera_id: string;
  project_name?: string | null;
  project_status?: string | null;
  project_type?: string | null;
  district?: string | null;
  taluka?: string | null;
  locality?: string | null;
  pin_code?: string | null;
  promoter_details?: string | null;
  proposed_completion_date?: string | null;
  last_modified?: string | null;
  website_last_modified?: string | null;
  stored_last_modified?: string | null;
  action?: string | null;
  decision_status?: string | null;
  total_buildings?: number;
  bank_name?: string | null;
  raw_data?: Record<string, any> | null;
}

export interface JobScrapedDataResponse {
  job_id: string;
  district_name: string;
  total_count: number;
  scraped_count: number;
  skipped_count: number;
  failed_count: number;
  projects: ScrapedProjectItem[];
  export_files: {
    csv?: string | null;
    excel?: string | null;
    json?: string | null;
    sql?: string | null;
  };
}

export interface CaptchaHealthData {
  status: "healthy" | "degraded" | "unhealthy";
  status_label: string;
  timestamp: string;
  engine: {
    tesseract: {
      installed: boolean;
      path?: string | null;
      version?: string | null;
    };
    opencv: {
      installed: boolean;
      version?: string | null;
      clahe_supported: boolean;
    };
    pillow: {
      installed: boolean;
      version?: string | null;
    };
  };
  self_test?: {
    executed: boolean;
    passed: boolean;
    latency_ms: number;
    test_expected?: string;
    test_recognized?: string;
    error?: string | null;
  } | null;
  metrics: {
    total_attempts: number;
    total_accepted: number;
    total_rejected: number;
    total_blocked: number;
    total_refreshes: number;
    solve_rate_percent: number;
    avg_attempts_per_solve: number;
    last_attempt_at?: string | null;
    last_solved_at?: string | null;
    recent_events: Array<{
      id: number;
      job_id: string;
      level: string;
      message: string;
      timestamp?: string | null;
    }>;
  };
}
