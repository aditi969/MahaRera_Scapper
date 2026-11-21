import {
  CompletionPoint,
  DataQualityMetrics,
  DistrictStat,
  MapProject,
  OverviewKPIs,
  ProjectDetail,
  ProjectListResponse,
  ProjectTypeStat,
  ScrapeJobItem,
  ScrapeLogItem,
  ScrapePreviewRequest,
  ScrapePreviewResponse,
  StartScrapeRequest,
  StatusStat,
  TrendPoint,
} from "../types";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // In browser, use relative path so Next.js proxies to backend without CORS friction
  if (typeof window !== "undefined") {
    return "";
  }
  return "http://127.0.0.1:8000";
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${getApiBase()}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`API Error ${res.status}: ${errorText || res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Request to ${endpoint} failed:`, err);
    throw err;
  }
}

export async function fetchProjects(params: {
  page?: number;
  pageSize?: number;
  search?: string;
  district?: string;
  status?: string;
  projectType?: string;
  sortBy?: string;
  sortDir?: string;
}): Promise<ProjectListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", params.page.toString());
  if (params.pageSize) query.set("page_size", params.pageSize.toString());
  if (params.search) query.set("search", params.search);
  if (params.district) query.set("district", params.district);
  if (params.status) query.set("status", params.status);
  if (params.projectType) query.set("project_type", params.projectType);
  if (params.sortBy) query.set("sort_by", params.sortBy);
  if (params.sortDir) query.set("sort_dir", params.sortDir);

  return request<ProjectListResponse>(`/api/projects?${query.toString()}`);
}

export async function fetchProject(reraId: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/projects/${encodeURIComponent(reraId)}`);
}

export async function fetchMapLocations(params?: {
  district?: string;
  status?: string;
  projectType?: string;
}): Promise<MapProject[]> {
  const query = new URLSearchParams();
  if (params?.district) query.set("district", params.district);
  if (params?.status) query.set("status", params.status);
  if (params?.projectType) query.set("project_type", params.projectType);

  return request<MapProject[]>(`/api/projects/locations?${query.toString()}`);
}

export async function fetchOverview(): Promise<OverviewKPIs> {
  return request<OverviewKPIs>("/api/analytics/overview");
}

export async function fetchDistricts(): Promise<DistrictStat[]> {
  return request<DistrictStat[]>("/api/analytics/districts");
}

export async function fetchStatusStats(): Promise<StatusStat[]> {
  return request<StatusStat[]>("/api/analytics/status");
}

export async function fetchProjectTypes(): Promise<ProjectTypeStat[]> {
  return request<ProjectTypeStat[]>("/api/analytics/project-types");
}

export async function fetchRegistrationTrend(): Promise<TrendPoint[]> {
  return request<TrendPoint[]>("/api/analytics/registration-trend");
}

export async function fetchCompletionTrend(): Promise<CompletionPoint[]> {
  return request<CompletionPoint[]>("/api/analytics/completion-trend");
}

export async function fetchDataQuality(): Promise<DataQualityMetrics> {
  return request<DataQualityMetrics>("/api/data-quality");
}

export async function fetchScrapeJobs(): Promise<ScrapeJobItem[]> {
  return request<ScrapeJobItem[]>("/api/scraper/jobs");
}

export async function fetchScrapeLogs(jobId: string): Promise<ScrapeLogItem[]> {
  return request<ScrapeLogItem[]>(`/api/scraper/logs/${jobId}`);
}

export async function previewScrapeJob(data: ScrapePreviewRequest): Promise<ScrapePreviewResponse> {
  return request<ScrapePreviewResponse>("/api/scraper/preview", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function startScrapeJob(data: StartScrapeRequest): Promise<ScrapeJobItem> {
  return request<ScrapeJobItem>("/api/scraper/start", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function cancelScrapeJob(jobId: string): Promise<{ message: string; status: string }> {
  return request<{ message: string; status: string }>(`/api/scraper/cancel/${jobId}`, {
    method: "POST",
  });
}

export async function retryScrapeJob(jobId: string): Promise<ScrapeJobItem> {
  return request<ScrapeJobItem>(`/api/scraper/retry/${jobId}`, {
    method: "POST",
  });
}

export async function clearScrapeJobs(): Promise<{ message: string; cleared_count: number }> {
  return request<{ message: string; cleared_count: number }>("/api/scraper/jobs", {
    method: "DELETE",
  });
}

export async function deleteScrapeJob(jobId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/scraper/jobs/${jobId}`, {
    method: "DELETE",
  });
}

export async function fetchHealth(): Promise<{
  status: string;
  app_name: string;
  version: string;
  database: string;
  total_projects: number;
  timestamp: string;
}> {
  return request("/api/health");
}

