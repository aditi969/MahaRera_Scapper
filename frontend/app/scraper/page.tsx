"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Play,
  Square,
  Terminal,
  Activity,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Clock,
  ChevronDown,
  ChevronUp,
  Settings,
  Search,
  RotateCcw,
  Eye,
  Calendar,
  MapPin,
  Building,
  Database,
  Sparkles,
  ArrowRight,
  Filter,
  Layers,
  X,
  FileSpreadsheet,
  Trash2,
  Download,
  Maximize2,
  Minimize2,
  Eraser,
} from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import {
  fetchScrapeJobs,
  fetchScrapeLogs,
  startScrapeJob,
  cancelScrapeJob,
  retryScrapeJob,
  previewScrapeJob,
  clearScrapeJobs,
  deleteScrapeJob,
} from "../../lib/api";
import {
  ScrapeJobItem,
  ScrapeLogItem,
  ScrapePreviewResponse,
  ScrapePreviewRecord,
  StartScrapeRequest,
} from "../../types";

// Official 36 Maharashtra Districts & Codes
const MAHARASHTRA_DISTRICTS = [
  { name: "All / Any District", code: "" },
  { name: "Ahmednagar", code: "522" },
  { name: "Akola", code: "501" },
  { name: "Amravati", code: "503" },
  { name: "Aurangabad", code: "515" },
  { name: "Beed", code: "523" },
  { name: "Bhandara", code: "506" },
  { name: "Buldhana", code: "500" },
  { name: "Chandrapur", code: "509" },
  { name: "Dhule", code: "498" },
  { name: "Gadchiroli", code: "508" },
  { name: "Gondia", code: "507" },
  { name: "Hingoli", code: "512" },
  { name: "Jalgaon", code: "499" },
  { name: "Jalna", code: "514" },
  { name: "Kolhapur", code: "530" },
  { name: "Latur", code: "524" },
  { name: "Mumbai City", code: "519" },
  { name: "Mumbai Suburban", code: "518" },
  { name: "Nagpur", code: "505" },
  { name: "Nanded", code: "511" },
  { name: "Nandurbar", code: "497" },
  { name: "Nashik", code: "516" },
  { name: "Osmanabad", code: "525" },
  { name: "Palghar", code: "532" },
  { name: "Parbhani", code: "513" },
  { name: "Pune", code: "521" },
  { name: "Raigarh", code: "520" },
  { name: "Ratnagiri", code: "528" },
  { name: "Sangli", code: "531" },
  { name: "Satara", code: "527" },
  { name: "Sindhudurg", code: "529" },
  { name: "Solapur", code: "526" },
  { name: "Thane", code: "517" },
  { name: "Wardha", code: "504" },
  { name: "Washim", code: "502" },
  { name: "Yavatmal", code: "510" },
];

export default function ScraperControlPage() {
  const [jobs, setJobs] = useState<ScrapeJobItem[]>([]);
  const [activeJob, setActiveJob] = useState<ScrapeJobItem | null>(null);
  const [logs, setLogs] = useState<ScrapeLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // MahaRERA Search Filter State (mirrors official portal)
  const [projectType, setProjectType] = useState<"Registered Projects" | "Revoked Projects">("Registered Projects");
  const [searchQuery, setSearchQuery] = useState("");
  const [pincode, setPincode] = useState("");
  const [completionDate, setCompletionDate] = useState("");
  const [stateName, setStateName] = useState("MAHARASHTRA");
  const [districtName, setDistrictName] = useState("All / Any District");
  const [districtCode, setDistrictCode] = useState("");

  // Advanced Filters & Page Scope
  const [division, setDivision] = useState("");
  const [taluka, setTaluka] = useState("");
  const [village, setVillage] = useState("");
  const [usePageRange, setUsePageRange] = useState(false); // Default: All available pages (user can enable custom range)
  const [startPage, setStartPage] = useState(1);
  const [endPage, setEndPage] = useState(2);
  const [maxWorkers, setMaxWorkers] = useState(1);
  const [headless, setHeadless] = useState(true);
  const [smartDateCheck, setSmartDateCheck] = useState(true);

  // Real-time Page Range Validation
  const pageRangeError = usePageRange
    ? startPage < 1
      ? "Start Page must be at least 1."
      : endPage < 1
      ? "End Page must be at least 1."
      : startPage > endPage
      ? `Start Page (${startPage}) must be less than or equal to End Page (${endPage}).`
      : null
    : null;

  // UI Drawer / Modal States
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showLogs, setShowLogs] = useState(true);
  const [isMaximizedLogs, setIsMaximizedLogs] = useState(false);
  const [autoScrollLogs, setAutoScrollLogs] = useState(true);
  const [logSearchQuery, setLogSearchQuery] = useState("");
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<ScrapePreviewResponse | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const handleDownloadLogs = () => {
    if (!logs || logs.length === 0) return;
    const content = logs
      .map(
        (l) =>
          `[${new Date(l.created_at).toLocaleString()}] [${l.level}] ${l.message}`
      )
      .join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `maharera_scrape_logs_${activeJob?.job_id || "job"}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const isRunning =
    activeJob?.status === "RUNNING" ||
    activeJob?.status === "STARTING" ||
    jobs.some((j) => j.status === "RUNNING" || j.status === "STARTING");

  const [clearingHistory, setClearingHistory] = useState(false);

  const loadJobs = async (selectedJobId?: string) => {
    try {
      setError(null);
      const data = await fetchScrapeJobs();
      setJobs(data);

      if (data.length > 0) {
        const targetId = selectedJobId || activeJob?.job_id || data[0].job_id;
        const target = data.find((j) => j.job_id === targetId) || data[0];
        setActiveJob(target);
        loadLogs(target.job_id);
      } else {
        setActiveJob(null);
        setLogs([]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load scrape jobs from database.");
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear all completed, failed, and cancelled scraping job history records?")) {
      return;
    }
    setClearingHistory(true);
    try {
      await clearScrapeJobs();
      setActiveJob(null);
      setLogs([]);
      await loadJobs();
    } catch (err: any) {
      alert(err?.message || "Failed to clear job history.");
    } finally {
      setClearingHistory(false);
    }
  };

  const handleDeleteSingleJob = async (jobId: string) => {
    if (!window.confirm(`Delete job record "${jobId}"?`)) {
      return;
    }
    try {
      await deleteScrapeJob(jobId);
      if (activeJob?.job_id === jobId) {
        setActiveJob(null);
        setLogs([]);
      }
      await loadJobs();
    } catch (err: any) {
      alert(err?.message || "Failed to delete job.");
    }
  };

  const loadLogs = async (jobId: string) => {
    try {
      const jobLogs = await fetchScrapeLogs(jobId);
      setLogs(jobLogs);
    } catch (e) {
      console.error("Failed to load logs:", e);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  // Periodic status poll when job is running
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      if (activeJob) {
        loadJobs(activeJob.job_id);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [isRunning, activeJob?.job_id]);

  // Auto-scroll logs
  useEffect(() => {
    if (showLogs && autoScrollLogs) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, showLogs, autoScrollLogs]);

  // WebSocket live connection
  useEffect(() => {
    if (!activeJob) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const host =
      typeof window !== "undefined" && window.location.hostname === "localhost"
        ? "localhost"
        : "127.0.0.1";
    const wsUrl = `ws://${host}:8000/ws/scraper/${activeJob.job_id}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "log") {
            setLogs((prev) => [
              ...prev,
              {
                id: Date.now(),
                job_id: activeJob.job_id,
                level: payload.level || "INFO",
                message: payload.message,
                created_at: payload.timestamp || new Date().toISOString(),
              },
            ]);
          } else if (payload.type === "complete" || payload.type === "status") {
            setActiveJob((prev) =>
              prev
                ? {
                    ...prev,
                    status: payload.status,
                    summary_json: payload.summary || prev.summary_json,
                  }
                : null
            );
            loadJobs(activeJob.job_id);
          }
        } catch (err) {
          console.error("WS parse error:", err);
        }
      };

      ws.onerror = () => {
        // Fallback to polling
      };
    } catch (e) {
      console.error("WS connection error:", e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [activeJob?.job_id]);

  const handleResetFilters = () => {
    setProjectType("Registered Projects");
    setSearchQuery("");
    setPincode("");
    setCompletionDate("");
    setStateName("MAHARASHTRA");
    setDistrictName("All / Any District");
    setDistrictCode("");
    setDivision("");
    setTaluka("");
    setVillage("");
    setUsePageRange(false);
    setStartPage(1);
    setEndPage(2);
    setSmartDateCheck(true);
  };

  const handlePreview = async () => {
    setPreviewLoading(true);
    setShowPreviewModal(true);
    try {
      const res = await previewScrapeJob({
        district_name: districtName === "All / Any District" ? "" : districtName,
        search_query: searchQuery,
        pincode: pincode,
        completion_date: completionDate,
        project_type_category: projectType,
      });
      setPreviewData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to preview matching projects.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleStartJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (usePageRange && pageRangeError) {
      setError(pageRangeError);
      return;
    }
    if (isRunning) {
      setError("A scraping job is already active. Please wait or cancel it first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload: StartScrapeRequest = {
        district_name: districtName === "All / Any District" ? "" : districtName,
        district_code: districtCode,
        start_page: usePageRange ? startPage : 1,
        end_page: usePageRange ? endPage : null,
        scrape_all_pages: !usePageRange,
        max_workers: maxWorkers,
        headless: headless,
        project_type_category: projectType,
        search_query: searchQuery,
        pincode: pincode,
        completion_date: completionDate,
        state: stateName,
        division: division,
        taluka: taluka,
        village: village,
        smart_date_check: smartDateCheck,
      };

      const newJob = await startScrapeJob(payload);
      setActiveJob(newJob);
      setLogs([]);
      setShowLogs(true);
      await loadJobs(newJob.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start scraping job.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    try {
      await cancelScrapeJob(activeJob.job_id);
      setActiveJob((prev) => (prev ? { ...prev, status: "CANCELLED" } : null));
      await loadJobs(activeJob.job_id);
    } catch (err: any) {
      setError("Failed to cancel job: " + (err?.message || ""));
    }
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      const newJob = await retryScrapeJob(jobId);
      setActiveJob(newJob);
      await loadJobs(newJob.job_id);
      await loadLogs(newJob.job_id);
    } catch (err: any) {
      setError("Failed to retry scrape job: " + (err?.message || ""));
    }
  };

  // Compute progress percentage
  const calculateProgress = () => {
    if (!activeJob) return 0;
    if (activeJob.status === "COMPLETED") return 100;
    if (activeJob.end_page && activeJob.end_page >= activeJob.start_page) {
      const totalPages = Math.max(1, activeJob.end_page - activeJob.start_page + 1);
      const cur = (activeJob.current_page || activeJob.start_page) - activeJob.start_page + 1;
      const pct = Math.round((cur / totalPages) * 100);
      return Math.min(Math.max(pct, 5), 95);
    }
    // When in All Pages mode without fixed upper bound
    return 60;
  };

  // Extract smart summary counters from activeJob
  const summary = activeJob?.summary_json || {};
  const totalDiscovered = summary.total_discovered || activeJob?.projects_found || 0;
  const newProjects = summary.new_projects || 0;
  const existingChecked = summary.existing_checked || 0;
  const unchangedSkipped = summary.unchanged_skipped || 0;
  const updatedRescrapped = summary.updated_rescrapped || 0;
  const successfulScraped = summary.successful_scraped || activeJob?.projects_extracted || 0;
  const failedProjects = summary.failed_projects || activeJob?.projects_failed || 0;
  const totalSavedOrUpdated = summary.total_saved_or_updated || (newProjects + updatedRescrapped);
  const projectDetailsMap = summary.project_details || {};
  const projectDetailsList = Object.values(projectDetailsMap);

  return (
    <div className="space-y-6">
      <PageHeader
        title="MahaRERA Smart Scraper & Filter Hub"
        subtitle="Search, filter, compare Last Modified dates, and scrape complete 55-field MahaRERA project records"
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Scraper" }]}
        action={
          <button
            onClick={() => loadJobs()}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition shadow-xs"
          >
            <RefreshCw size={13} /> Refresh
          </button>
        }
      />

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-xs font-bold text-red-900">Notice</h4>
            <p className="text-xs text-red-700 mt-0.5">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-xs text-red-500 hover:text-red-700 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Grid: Left Column (Filters & Start Scrape) & Right Column (Telemetry & Results) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ======================================================== */}
        {/* LEFT COLUMN: MAHARERA SEARCH FILTERS (5 Columns)        */}
        {/* ======================================================== */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Filter size={16} className="text-blue-600" /> Search MahaRERA Projects
              </h2>
              {isRunning ? (
                <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 animate-pulse">
                  Job In Progress
                </span>
              ) : (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-xs text-gray-500 hover:text-blue-600 flex items-center gap-1 transition"
                  title="Reset all filters to default"
                >
                  <RotateCcw size={12} /> Reset
                </button>
              )}
            </div>

            <form onSubmit={handleStartJob} className="space-y-4 text-xs">
              {/* Filter 1: Project Type Radio Options (Direct from Screenshot) */}
              <div>
                <label className="block font-semibold text-gray-800 mb-1.5">
                  Project Type
                </label>
                <div className="flex items-center gap-5 pt-0.5">
                  <label className="inline-flex items-center gap-2 cursor-pointer font-medium text-gray-700">
                    <input
                      type="radio"
                      name="projectType"
                      value="Registered Projects"
                      checked={projectType === "Registered Projects"}
                      onChange={() => setProjectType("Registered Projects")}
                      disabled={isRunning}
                      className="text-blue-600 focus:ring-blue-500 w-4 h-4"
                    />
                    <span>Registered Projects</span>
                  </label>
                  <label className="inline-flex items-center gap-2 cursor-pointer font-medium text-gray-700">
                    <input
                      type="radio"
                      name="projectType"
                      value="Revoked Projects"
                      checked={projectType === "Revoked Projects"}
                      onChange={() => setProjectType("Revoked Projects")}
                      disabled={isRunning}
                      className="text-blue-600 focus:ring-blue-500 w-4 h-4"
                    />
                    <span>Revoked Projects</span>
                  </label>
                </div>
              </div>

              {/* Filter 2: Project Name / MahaRERA Registration Number (Screenshot input) */}
              <div>
                <label className="block font-medium text-gray-700 mb-1">
                  Project Name / MahaRERA Registration Number
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    disabled={isRunning}
                    placeholder="e.g. Godrej, A. M. Residency, or P51900000070"
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                  <Search size={14} className="absolute left-2.5 top-2.5 text-gray-400" />
                </div>
              </div>

              {/* Filter 3 & 4: Pincode and Completion Date */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    Pincode
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      maxLength={6}
                      value={pincode}
                      disabled={isRunning}
                      placeholder="e.g. 400010"
                      onChange={(e) => setPincode(e.target.value.replace(/\D/g, ""))}
                      className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                    <MapPin size={14} className="absolute left-2.5 top-2.5 text-gray-400" />
                  </div>
                </div>

                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    Completion Date
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      value={completionDate}
                      disabled={isRunning}
                      onChange={(e) => setCompletionDate(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                    />
                  </div>
                </div>
              </div>

              {/* Filter 5 & 6: State and District (Screenshot dropdowns) */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    State
                  </label>
                  <select
                    value={stateName}
                    disabled
                    className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-700 font-semibold cursor-not-allowed"
                  >
                    <option value="MAHARASHTRA">MAHARASHTRA</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    District
                  </label>
                  <select
                    value={districtName}
                    disabled={isRunning}
                    onChange={(e) => {
                      const sel = MAHARASHTRA_DISTRICTS.find((d) => d.name === e.target.value);
                      if (sel) {
                        setDistrictName(sel.name);
                        setDistrictCode(sel.code);
                      }
                    }}
                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                  >
                    {MAHARASHTRA_DISTRICTS.map((d) => (
                      <option key={d.name} value={d.name}>
                        {d.name} {d.code ? `(${d.code})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Smart Last Modified Date Check Feature Card */}
              <div className="p-3 bg-blue-50/70 border border-blue-200/80 rounded-xl space-y-1.5">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={smartDateCheck}
                    disabled={isRunning}
                    onChange={(e) => setSmartDateCheck(e.target.checked)}
                    className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 w-4 h-4"
                  />
                  <div>
                    <span className="font-semibold text-blue-900 flex items-center gap-1.5">
                      <Sparkles size={14} className="text-blue-600" /> Smart Last Modified Date Check
                    </span>
                    <p className="text-[11px] text-blue-700 leading-relaxed mt-0.5">
                      Compares website Last Modified date against local database. Unchanged projects are <strong>skipped</strong> from re-downloading to save bandwidth, while matching records are always preserved in your exported CSV, Excel, and SQL files. <em>Uncheck to force full re-scrape from scratch.</em>
                    </p>
                  </div>
                </label>
              </div>

              {/* Optional Page Range Selection & Pagination Mode */}
              <div className="pt-1 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-gray-800">
                    Scraping Page Scope
                  </label>
                  <div className="inline-flex p-0.5 bg-gray-100 rounded-lg border border-gray-200 text-xs">
                    <button
                      type="button"
                      disabled={isRunning}
                      onClick={() => setUsePageRange(false)}
                      className={`px-2.5 py-1 rounded-md font-medium transition ${
                        !usePageRange
                          ? "bg-white text-blue-700 shadow-xs font-semibold"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      🌐 All Pages
                    </button>
                    <button
                      type="button"
                      disabled={isRunning}
                      onClick={() => setUsePageRange(true)}
                      className={`px-2.5 py-1 rounded-md font-medium transition ${
                        usePageRange
                          ? "bg-white text-blue-700 shadow-xs font-semibold"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      📑 Page Range
                    </button>
                  </div>
                </div>

                {!usePageRange ? (
                  <div className="p-3 bg-emerald-50/70 border border-emerald-200/80 rounded-xl flex items-start gap-2.5 text-xs">
                    <Layers size={15} className="text-emerald-600 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-semibold text-emerald-950 block">
                        Entire Website / All Results Mode
                      </span>
                      <p className="text-[11px] text-emerald-700 leading-relaxed mt-0.5">
                        Scrapes all matching projects across every available pagination page until the entire dataset is extracted.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-gray-50/70 border border-gray-200 rounded-xl space-y-2">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Start Page
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={startPage}
                          disabled={isRunning}
                          onChange={(e) => setStartPage(parseInt(e.target.value) || 0)}
                          className={`w-full px-3 py-1.5 text-xs bg-white border rounded-lg focus:outline-none focus:ring-2 disabled:bg-gray-100 ${
                            startPage < 1 ? "border-rose-400 focus:ring-rose-400" : "border-gray-300 focus:ring-blue-500"
                          }`}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          End Page
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={endPage}
                          disabled={isRunning}
                          onChange={(e) => setEndPage(parseInt(e.target.value) || 0)}
                          className={`w-full px-3 py-1.5 text-xs bg-white border rounded-lg focus:outline-none focus:ring-2 disabled:bg-gray-100 ${
                            endPage < 1 || endPage < startPage ? "border-rose-400 focus:ring-rose-400" : "border-gray-300 focus:ring-blue-500"
                          }`}
                        />
                      </div>
                    </div>

                    {/* Real-time Validation Error Banner */}
                    {pageRangeError && (
                      <div className="flex items-center gap-1.5 text-[11px] font-medium text-rose-700 bg-rose-50 px-2.5 py-1.5 rounded-lg border border-rose-200">
                        <AlertCircle size={13} className="shrink-0 text-rose-600" />
                        <span>{pageRangeError}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Advanced Settings & Sub-regional Filters */}
              <div className="pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 font-medium"
                >
                  <Settings size={13} />
                  <span>Sub-Regional & Engine Settings</span>
                  {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>

                {showAdvanced && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-3 border border-gray-200/80">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block font-medium text-gray-600 mb-0.5">Division</label>
                        <input
                          type="text"
                          value={division}
                          disabled={isRunning}
                          placeholder="e.g. Konkan"
                          onChange={(e) => setDivision(e.target.value)}
                          className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded-md text-xs"
                        />
                      </div>
                      <div>
                        <label className="block font-medium text-gray-600 mb-0.5">Taluka</label>
                        <input
                          type="text"
                          value={taluka}
                          disabled={isRunning}
                          placeholder="e.g. Panvel"
                          onChange={(e) => setTaluka(e.target.value)}
                          className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded-md text-xs"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block font-medium text-gray-600 mb-0.5">Village / Locality</label>
                      <input
                        type="text"
                        value={village}
                        disabled={isRunning}
                        placeholder="e.g. Kharghar"
                        onChange={(e) => setVillage(e.target.value)}
                        className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded-md text-xs"
                      />
                    </div>
                    <div className="flex items-center justify-between pt-1">
                      <div>
                        <label className="block font-medium text-gray-600 mb-0.5">Workers</label>
                        <select
                          value={maxWorkers}
                          disabled={isRunning}
                          onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 1)}
                          className="px-2 py-1 bg-white border border-gray-300 rounded text-xs"
                        >
                          <option value="1">1 Worker</option>
                          <option value="2">2 Workers</option>
                        </select>
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer pt-3">
                        <input
                          type="checkbox"
                          checked={headless}
                          disabled={isRunning}
                          onChange={(e) => setHeadless(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-gray-700 text-xs">Headless Chrome</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons: Preview & Launch */}
              <div className="space-y-2 pt-2">
                <button
                  type="submit"
                  disabled={loading || isRunning || (usePageRange && !!pageRangeError)}
                  className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-xs"
                >
                  {loading ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      <span>Initializing Job...</span>
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      <span>Launch Scraping Job</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={previewLoading || isRunning}
                  className="w-full py-2 px-4 bg-gray-50 hover:bg-gray-100 text-gray-700 font-medium rounded-lg border border-gray-200 transition flex items-center justify-center gap-2 text-xs"
                >
                  <Eye size={13} className="text-blue-600" />
                  <span>Preview Matching Projects in Database</span>
                </button>
              </div>
            </form>
          </div>

          {/* Active Configuration Summary */}
          <div className="mt-5 pt-3 border-t border-gray-100 text-[11px] text-gray-500 bg-gray-50/70 p-2.5 rounded-lg border border-gray-200/60">
            <span className="font-semibold text-gray-700 block mb-1">Target Search Scope:</span>
            <div className="space-y-0.5">
              <span>Type: <strong>{projectType}</strong></span>
              {searchQuery && <span> • Query: <strong>&ldquo;{searchQuery}&rdquo;</strong></span>}
              {pincode && <span> • Pincode: <strong>{pincode}</strong></span>}
              {districtName && <span> • District: <strong>{districtName}</strong></span>}
              <span> • Scope: <strong>{usePageRange ? `Pages ${startPage}–${endPage}` : "All Available Pages (Auto)"}</strong></span>
              <span> • Smart Date Check: <strong>{smartDateCheck ? "ON" : "OFF"}</strong></span>
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* RIGHT COLUMN: REAL-TIME TELEMETRY & RESULTS (7 Columns)  */}
        {/* ======================================================== */}
        <div className="lg:col-span-7 space-y-6">
          {/* Section B1: Active Job Status & Summary KPIs */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <div>
                <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <Activity size={16} className="text-emerald-600" /> Active Job Status & Summary
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Real-time telemetry and smart date-based extraction counters
                </p>
              </div>

              {activeJob && (
                <div className="flex items-center gap-2">
                  <Badge
                    variant={
                      activeJob.status === "COMPLETED"
                        ? "success"
                        : activeJob.status === "RUNNING" || activeJob.status === "STARTING"
                        ? "primary"
                        : activeJob.status === "CANCELLED"
                        ? "neutral"
                        : activeJob.status === "COMPLETED_WITH_ERRORS"
                        ? "warning"
                        : "danger"
                    }
                  >
                    {activeJob.status}
                  </Badge>

                  {(activeJob.status === "RUNNING" || activeJob.status === "STARTING") && (
                    <button
                      onClick={handleCancelJob}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-md hover:bg-red-100 transition"
                      title="Cancel running scrape job"
                    >
                      <Square size={11} /> Cancel
                    </button>
                  )}
                  {(activeJob.status === "COMPLETED_WITH_ERRORS" || activeJob.status === "FAILED") && (
                    <button
                      onClick={() => handleRetryJob(activeJob.job_id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-amber-800 bg-amber-100/90 hover:bg-amber-200 border border-amber-300 rounded-md transition shadow-2xs cursor-pointer"
                      title="Retry failed projects and pages for this job"
                    >
                      <RotateCcw size={12} /> Retry Failed Items
                    </button>
                  )}
                </div>
              )}
            </div>

            {activeJob ? (
              <div className="space-y-4">
                {/* Job Metadata Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 bg-gray-50 rounded-xl border border-gray-200/70 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Job Identifier</span>
                    <span className="font-mono font-medium text-gray-800 truncate block">
                      {activeJob.job_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Target District</span>
                    <span className="font-semibold text-gray-800 block">
                      {activeJob.district_name || "Custom Filters"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Page Scope</span>
                    <span className="font-semibold text-gray-800 block">
                      {activeJob.filters_json?.scrape_all_pages || !activeJob.end_page
                        ? `Pages ${activeJob.start_page}–All (Auto)`
                        : `Pages ${activeJob.start_page}–${activeJob.end_page}`}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Started At</span>
                    <span className="font-mono text-gray-600 block">
                      {activeJob.started_at ? new Date(activeJob.started_at).toLocaleTimeString() : "—"}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-medium text-gray-700 flex items-center gap-1.5">
                      {activeJob.status === "RUNNING" ? (
                        <RefreshCw size={12} className="animate-spin text-blue-600" />
                      ) : activeJob.status === "COMPLETED" ? (
                        <CheckCircle2 size={12} className="text-emerald-600" />
                      ) : (
                        <Clock size={12} className="text-gray-400" />
                      )}
                      <span>
                        {activeJob.status === "RUNNING"
                          ? `Processing Page ${activeJob.current_page || activeJob.start_page}...`
                          : activeJob.status === "COMPLETED"
                          ? "Extraction completed successfully."
                          : `Job ${activeJob.status.toLowerCase()}`}
                      </span>
                    </span>
                    <span className="font-mono text-gray-500">
                      {calculateProgress()}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        activeJob.status === "COMPLETED"
                          ? "bg-emerald-500"
                          : activeJob.status === "FAILED"
                          ? "bg-red-500"
                          : "bg-blue-600"
                      }`}
                      style={{ width: `${calculateProgress()}%` }}
                    />
                  </div>
                </div>

                {/* Error / Diagnostic Note Alert */}
                {(activeJob.error_message || activeJob.status === "COMPLETED_WITH_ERRORS" || activeJob.status === "FAILED") && (
                  <div className={`flex items-start gap-2.5 p-3 rounded-xl text-xs shadow-2xs ${
                    activeJob.status === "FAILED" ? "bg-rose-50 border border-rose-200 text-rose-900" : "bg-amber-50 border border-amber-200 text-amber-900"
                  }`}>
                    <AlertCircle size={15} className={`mt-0.5 shrink-0 ${activeJob.status === "FAILED" ? "text-rose-600" : "text-amber-600"}`} />
                    <div className="w-full">
                      <span className="font-semibold block">Execution Diagnostic & Error Details:</span>
                      <p className="text-[11px] leading-relaxed mt-0.5">
                        {activeJob.error_message || (activeJob.status === "COMPLETED_WITH_ERRORS"
                          ? "Some pages or project detail pages could not be extracted during this run. See the Failed counter in the metrics grid and Diagnostic Logs below for exact reasons."
                          : "Job terminated due to an error. Check the Process Logs below for the full traceback.")}
                      </p>
                    </div>
                  </div>
                )}

                {/* Comprehensive 8-Metric Smart Summary Grid */}
                <div>
                  <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wider mb-2">
                    Scraping Summary & Smart Metrics
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                    <div className="p-2.5 bg-gray-50 border border-gray-200/80 rounded-lg">
                      <span className="text-gray-400 text-[10px] uppercase font-bold block">Discovered</span>
                      <span className="text-base font-bold text-gray-800">{totalDiscovered}</span>
                    </div>

                    <div className="p-2.5 bg-blue-50/60 border border-blue-200/70 rounded-lg">
                      <span className="text-blue-600 text-[10px] uppercase font-bold block">New Found</span>
                      <span className="text-base font-bold text-blue-700">{newProjects}</span>
                    </div>

                    <div className="p-2.5 bg-amber-50/60 border border-amber-200/70 rounded-lg">
                      <span className="text-amber-700 text-[10px] uppercase font-bold block">Updated Re-scraped</span>
                      <span className="text-base font-bold text-amber-800">{updatedRescrapped}</span>
                    </div>

                    <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                      <span className="text-slate-600 text-[10px] uppercase font-bold block">Unchanged Skipped</span>
                      <span className="text-base font-bold text-slate-700">{unchangedSkipped}</span>
                    </div>

                    <div className="p-2.5 bg-emerald-50/60 border border-emerald-200/70 rounded-lg">
                      <span className="text-emerald-700 text-[10px] uppercase font-bold block">Scraped OK</span>
                      <span className="text-base font-bold text-emerald-800">{successfulScraped}</span>
                    </div>

                    <div className="p-2.5 bg-red-50/60 border border-red-200/70 rounded-lg">
                      <span className="text-red-600 text-[10px] uppercase font-bold block">Failed</span>
                      <span className="text-base font-bold text-red-700">{failedProjects}</span>
                    </div>

                    <div className="p-2.5 bg-indigo-50/60 border border-indigo-200/70 rounded-lg">
                      <span className="text-indigo-700 text-[10px] uppercase font-bold block">Existing Checked</span>
                      <span className="text-base font-bold text-indigo-800">{existingChecked}</span>
                    </div>

                    <div className="p-2.5 bg-emerald-50/80 border border-emerald-300 rounded-lg">
                      <span className="text-emerald-800 text-[10px] uppercase font-bold block">Saved / Updated</span>
                      <span className="text-base font-bold text-emerald-900">{totalSavedOrUpdated}</span>
                    </div>
                  </div>
                </div>

                {/* Individual Projects Status Table */}
                {projectDetailsList.length > 0 && (
                  <div className="pt-2">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">
                        Discovered Projects & Actions Taken ({projectDetailsList.length})
                      </h4>
                    </div>
                    <div className="max-h-56 overflow-y-auto border border-gray-200 rounded-lg overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider font-semibold border-b border-gray-200 text-[10px]">
                          <tr>
                            <th className="py-2 px-3">RERA ID</th>
                            <th className="py-2 px-3">Project Name</th>
                            <th className="py-2 px-2 text-center">Website Date</th>
                            <th className="py-2 px-2 text-center">Stored Date</th>
                            <th className="py-2 px-3 text-right">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {projectDetailsList.map((item: any, idx: number) => {
                            const isSkipped = item.status === "UNCHANGED_SKIPPED";
                            const isUpdated = item.status === "UPDATED_RESCRAPPED";
                            const isNew = item.status === "NEW";
                            const isFailed = item.status === "FAILED";

                            return (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="py-2 px-3 font-mono font-medium text-gray-900">
                                  {item.rera_id || "—"}
                                </td>
                                <td className="py-2 px-3 text-gray-800 font-medium truncate max-w-[150px]">
                                  {item.project_name || "—"}
                                </td>
                                <td className="py-2 px-2 text-center font-mono text-[11px] text-gray-600">
                                  {item.website_last_modified || "—"}
                                </td>
                                <td className="py-2 px-2 text-center font-mono text-[11px] text-gray-500">
                                  {item.stored_last_modified || "None"}
                                </td>
                                <td className="py-2 px-3 text-right">
                                  {isSkipped && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
                                      SKIPPED
                                    </span>
                                  )}
                                  {isUpdated && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
                                      UPDATED
                                    </span>
                                  )}
                                  {isNew && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
                                      NEW
                                    </span>
                                  )}
                                  {isFailed && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-700 border border-red-200">
                                      FAILED
                                    </span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-400 text-xs">
                No active or selected scraping jobs found. Select filters on the left and click Launch.
              </div>
            )}

            {/* Enhanced Collapsible Execution Logs Drawer */}
            {activeJob && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <div className="flex flex-wrap items-center justify-between gap-2 bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                  <button
                    onClick={() => setShowLogs(!showLogs)}
                    className="flex items-center gap-2 text-xs font-semibold text-gray-700 hover:text-gray-900 transition"
                  >
                    <Terminal size={15} className="text-gray-500" />
                    <span>Diagnostics & Process Logs</span>
                    <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-gray-200/80 text-gray-700 rounded-full font-mono">
                      {logs.length} entries
                    </span>
                    {showLogs ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                  </button>

                  {showLogs && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {/* Search / Filter input */}
                      <div className="relative">
                        <Search size={12} className="absolute left-2 top-2 text-gray-400" />
                        <input
                          type="text"
                          value={logSearchQuery}
                          onChange={(e) => setLogSearchQuery(e.target.value)}
                          placeholder="Filter logs..."
                          className="pl-6 pr-2 py-1 text-[11px] bg-white border border-gray-200 rounded-md w-28 focus:w-40 focus:outline-hidden focus:border-blue-400 transition-all font-sans"
                        />
                      </div>

                      {/* Auto-scroll toggle */}
                      <button
                        onClick={() => setAutoScrollLogs(!autoScrollLogs)}
                        className={`px-2 py-1 text-[11px] font-medium rounded border transition flex items-center gap-1 ${
                          autoScrollLogs
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-white text-gray-500 border-gray-200 hover:bg-gray-50"
                        }`}
                        title={autoScrollLogs ? "Auto-scroll ON (click to pause)" : "Auto-scroll PAUSED (click to resume)"}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${autoScrollLogs ? "bg-blue-600 animate-pulse" : "bg-gray-400"}`} />
                        <span>Auto-scroll</span>
                      </button>

                      {/* Clear Logs */}
                      <button
                        onClick={handleClearLogs}
                        disabled={logs.length === 0}
                        className="p-1 px-2 text-[11px] font-medium text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-100 border border-gray-200 rounded transition flex items-center gap-1 disabled:opacity-40"
                        title="Clear logs from view"
                      >
                        <Eraser size={12} />
                        <span>Clear</span>
                      </button>

                      {/* Download Logs */}
                      <button
                        onClick={handleDownloadLogs}
                        disabled={logs.length === 0}
                        className="p-1 px-2 text-[11px] font-medium text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded transition flex items-center gap-1 disabled:opacity-40"
                        title="Download entire log audit trail as text file"
                      >
                        <Download size={12} />
                        <span>Download</span>
                      </button>

                      {/* Maximize / Standard size toggle */}
                      <button
                        onClick={() => setIsMaximizedLogs(!isMaximizedLogs)}
                        className="p-1 px-1.5 text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-100 border border-gray-200 rounded transition"
                        title={isMaximizedLogs ? "Restore normal size" : "Expand logs viewport"}
                      >
                        {isMaximizedLogs ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                      </button>
                    </div>
                  )}
                </div>

                {showLogs && (
                  <div
                    className={`mt-2 bg-gray-950 rounded-lg p-3 text-xs font-mono text-gray-200 overflow-y-auto space-y-1.5 shadow-inner border border-gray-800 transition-all ${
                      isMaximizedLogs ? "h-[540px]" : "h-96"
                    }`}
                  >
                    {logs.length === 0 ? (
                      <div className="text-gray-500 italic p-4 text-center">
                        Waiting for task execution logs... Launch or select a scraping job above to inspect real-time events.
                      </div>
                    ) : (
                      logs
                        .filter((l) =>
                          logSearchQuery
                            ? l.message.toLowerCase().includes(logSearchQuery.toLowerCase()) ||
                              l.level.toLowerCase().includes(logSearchQuery.toLowerCase())
                            : true
                        )
                        .map((log, index) => {
                          const isSuccess = log.level === "SUCCESS" || log.message.includes("✅") || log.message.includes("Success");
                          const isWarn = log.level === "WARNING" || log.message.includes("⚠️") || log.message.includes("Warning");
                          const isErr = log.level === "ERROR" || log.message.includes("❌") || log.message.includes("💥");

                          return (
                            <div key={index} className="flex items-start gap-2 leading-relaxed hover:bg-gray-900/60 p-0.5 rounded transition">
                              <span className="text-gray-500 shrink-0 text-[10px] select-none pt-0.5">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </span>
                              <span
                                className={`shrink-0 font-bold text-[9px] px-1.5 py-0.2 rounded border uppercase tracking-wider ${
                                  isErr
                                    ? "bg-rose-950 text-rose-300 border-rose-800"
                                    : isWarn
                                    ? "bg-amber-950 text-amber-300 border-amber-800"
                                    : isSuccess
                                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                                    : "bg-sky-950 text-sky-300 border-sky-800"
                                }`}
                              >
                                {log.level}
                              </span>
                              <span
                                className={`text-[11px] break-all select-text ${
                                  isErr
                                    ? "text-rose-200"
                                    : isWarn
                                    ? "text-amber-200"
                                    : isSuccess
                                    ? "text-emerald-200"
                                    : "text-gray-300"
                                }`}
                              >
                                {log.message}
                              </span>
                            </div>
                          );
                        })
                    )}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ======================================================== */}
      {/* SECTION C: RECENT JOB HISTORY                           */}
      {/* ======================================================== */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex flex-wrap justify-between items-center gap-3">
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Recent Scraping Job History</h3>
            <p className="text-xs text-gray-500">
              Audit log of completed and running scraping jobs with applied filters and metrics
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-mono">
              {jobs.length} Jobs Recorded
            </span>
            <button
              onClick={() => loadJobs(activeJob?.job_id)}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-700 bg-white hover:bg-gray-100 border border-gray-200 rounded-lg transition shadow-2xs cursor-pointer"
              title="Refresh job history list and current job status"
            >
              <RotateCcw size={12} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
            {jobs.length > 0 && (
              <button
                onClick={handleClearHistory}
                disabled={clearingHistory || isRunning}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition disabled:opacity-50"
                title="Clear all completed and failed job history records"
              >
                <Trash2 size={13} />
                <span>{clearingHistory ? "Clearing..." : "Clear History"}</span>
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider font-semibold border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Job Identifier</th>
                <th className="py-3 px-4">District / Filter</th>
                <th className="py-3 px-4 text-center">Page Scope</th>
                <th className="py-3 px-4 text-center">Projects Extracted</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4">Started</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-sans">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">
                    No scraping jobs recorded yet. Configure your search filters above and click &quot;Launch Scraping Job&quot;.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => {
                  const isSelected = activeJob?.job_id === job.job_id;
                  const filterDesc = job.filters_json?.search_query
                    ? `Query: ${job.filters_json.search_query}`
                    : job.filters_json?.pincode
                    ? `Pin: ${job.filters_json.pincode}`
                    : job.district_name || "All / Any District";

                  return (
                    <tr
                      key={job.job_id}
                      className={`hover:bg-gray-50/80 transition-colors ${
                        isSelected ? "bg-blue-50/40" : ""
                      }`}
                    >
                      <td className="py-3 px-4 font-mono font-medium text-gray-900">
                        {job.job_id}
                      </td>
                      <td className="py-3 px-4 font-semibold text-gray-800">
                        {filterDesc}
                      </td>
                      <td className="py-3 px-4 text-center font-mono text-gray-600">
                        {job.filters_json?.scrape_all_pages || !job.end_page ? (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-purple-50 text-purple-700 border border-purple-200">
                            Pages {job.start_page}–All
                          </span>
                        ) : (
                          `Pages ${job.start_page}–${job.end_page}`
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-semibold text-emerald-600">{job.projects_extracted || 0}</span>
                        <span className="text-[10px] text-gray-500 ml-1">projects</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          variant={
                            job.status === "COMPLETED"
                              ? "success"
                              : job.status === "RUNNING" || job.status === "STARTING"
                              ? "primary"
                              : job.status === "CANCELLED"
                              ? "neutral"
                              : job.status === "COMPLETED_WITH_ERRORS"
                              ? "warning"
                              : "danger"
                          }
                        >
                          {job.status}
                        </Badge>
                        {job.error_message && (
                          <div
                            className="mt-1 text-[10px] text-amber-800 bg-amber-50/80 border border-amber-200/80 rounded px-1.5 py-0.5 max-w-[210px] mx-auto text-left leading-tight cursor-help shadow-2xs"
                            title={job.error_message}
                          >
                            <span className="font-semibold text-amber-900">⚠️ Error: </span>
                            <span className="truncate inline-block max-w-[150px] align-bottom">{job.error_message}</span>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-500">
                        {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          {(job.status === "COMPLETED_WITH_ERRORS" || job.status === "FAILED") && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRetryJob(job.job_id);
                              }}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-md transition cursor-pointer"
                              title="Retry failed projects and pages for this job"
                            >
                              <RotateCcw size={11} /> Retry
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setActiveJob(job);
                              loadLogs(job.job_id);
                            }}
                            className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                              isSelected
                                ? "bg-blue-600 text-white"
                                : "bg-gray-100 hover:bg-gray-200 text-gray-700"
                            }`}
                          >
                            {isSelected ? "Viewing" : "View"}
                          </button>
                          {job.status !== "RUNNING" && job.status !== "STARTING" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteSingleJob(job.job_id);
                              }}
                              className="p-1 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded transition"
                              title="Delete this job record"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ======================================================== */}
      {/* PREVIEW MATCHING PROJECTS MODAL                          */}
      {/* ======================================================== */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/70">
              <div>
                <h3 className="font-bold text-gray-900 text-sm flex items-center gap-2">
                  <Database size={16} className="text-blue-600" /> Database Match Preview
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Projects currently stored that match your active filter criteria
                </p>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4 text-xs">
              {previewLoading ? (
                <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
                  <RefreshCw size={20} className="animate-spin text-blue-600" />
                  <span>Scanning local database records...</span>
                </div>
              ) : previewData ? (
                <>
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
                    <div>
                      <span className="font-bold text-blue-900 text-sm">
                        {previewData.matching_in_database} Projects Found in Database
                      </span>
                      <p className="text-[11px] text-blue-700 mt-0.5">
                        When scraping starts with Smart Check enabled, any matching project whose website Last Modified date is unchanged will be <strong>skipped</strong>.
                      </p>
                    </div>
                  </div>

                  {previewData.existing_projects.length > 0 ? (
                    <div className="border border-gray-200 rounded-lg overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-gray-50 text-gray-600 uppercase font-semibold text-[10px] border-b border-gray-200">
                          <tr>
                            <th className="p-2.5">RERA ID</th>
                            <th className="p-2.5">Project Name</th>
                            <th className="p-2.5">District</th>
                            <th className="p-2.5">Pincode</th>
                            <th className="p-2.5">Stored Modified</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {previewData.existing_projects.map((rec, i) => (
                            <tr key={i} className="hover:bg-gray-50">
                              <td className="p-2.5 font-mono font-medium text-gray-900">{rec.rera_id}</td>
                              <td className="p-2.5 text-gray-800 font-medium truncate max-w-[160px]">{rec.project_name || "—"}</td>
                              <td className="p-2.5 text-gray-600">{rec.district || "—"}</td>
                              <td className="p-2.5 font-mono text-gray-600">{rec.pincode || "—"}</td>
                              <td className="p-2.5 font-mono text-gray-700 font-semibold">{rec.last_modified || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-6 text-center text-gray-400 bg-gray-50 rounded-lg">
                      No matching records found in database for these filters. All discovered records on MahaRERA will be treated as <strong>NEW</strong>.
                    </div>
                  )}
                </>
              ) : null}
            </div>

            <div className="p-3 border-t border-gray-200 bg-gray-50/70 flex justify-end">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-3 py-1.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-100 text-xs"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
