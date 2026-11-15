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
  Layers,
  FileCheck,
} from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { Badge } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/ErrorState";
import {
  fetchScrapeJobs,
  fetchScrapeLogs,
  startScrapeJob,
  cancelScrapeJob,
} from "../../lib/api";
import { ScrapeJobItem, ScrapeLogItem } from "../../types";

const PRESET_DISTRICTS = [
  { name: "Raigarh", code: "520" },
  { name: "Mumbai City", code: "519" },
  { name: "Mumbai Suburban", code: "518" },
  { name: "Thane", code: "517" },
  { name: "Pune", code: "521" },
  { name: "Nashik", code: "516" },
  { name: "Nagpur", code: "505" },
];

export default function ScraperControlPage() {
  const [jobs, setJobs] = useState<ScrapeJobItem[]>([]);
  const [activeJob, setActiveJob] = useState<ScrapeJobItem | null>(null);
  const [logs, setLogs] = useState<ScrapeLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [districtName, setDistrictName] = useState("Raigarh");
  const [districtCode, setDistrictCode] = useState("520");
  const [startPage, setStartPage] = useState(1);
  const [endPage, setEndPage] = useState(2);
  const [maxWorkers, setMaxWorkers] = useState(1);
  const [headless, setHeadless] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  const isRunning =
    activeJob?.status === "RUNNING" ||
    activeJob?.status === "STARTING" ||
    jobs.some((j) => j.status === "RUNNING" || j.status === "STARTING");

  const loadJobs = async (selectedJobId?: string) => {
    try {
      setError(null);
      const data = await fetchScrapeJobs();
      setJobs(data);

      if (data.length > 0) {
        // If a specific job was requested or active, refresh it
        const targetId = selectedJobId || activeJob?.job_id || data[0].job_id;
        const target = data.find((j) => j.job_id === targetId) || data[0];
        setActiveJob(target);
        loadLogs(target.job_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load scrape jobs from database.");
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

  // Auto-scroll logs
  useEffect(() => {
    if (showLogs) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, showLogs]);

  // WebSocket live connection when activeJob is RUNNING or STARTING
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
          } else if (payload.type === "project_extracted") {
            setActiveJob((prev) =>
              prev
                ? {
                    ...prev,
                    projects_extracted: (prev.projects_extracted || 0) + 1,
                  }
                : null
            );
          } else if (payload.type === "page_started") {
            setActiveJob((prev) =>
              prev ? { ...prev, current_page: payload.page } : null
            );
          } else if (payload.type === "complete" || payload.type === "status") {
            setActiveJob((prev) =>
              prev ? { ...prev, status: payload.status } : null
            );
            loadJobs(activeJob.job_id);
          }
        } catch (err) {
          console.error("WS parse error:", err);
        }
      };

      ws.onerror = () => {
        // Fail silently; polling is fallback
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

  const handleStartJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (endPage < startPage) {
      setError("End page must be greater than or equal to start page.");
      return;
    }
    if (isRunning) {
      setError("A scraping job is already active. Please wait or cancel it first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const newJob = await startScrapeJob({
        district_name: districtName,
        district_code: districtCode,
        start_page: startPage,
        end_page: endPage,
        max_workers: maxWorkers,
        headless: headless,
      });
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

  // Compute progress percentage
  const calculateProgress = () => {
    if (!activeJob) return 0;
    if (activeJob.status === "COMPLETED") return 100;
    const totalPages = Math.max(1, activeJob.end_page - activeJob.start_page);
    const cur = (activeJob.current_page || activeJob.start_page) - activeJob.start_page;
    const pct = Math.round((cur / totalPages) * 100);
    return Math.min(Math.max(pct, 5), 95);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scraper Control Center"
        subtitle="Configure, execute, and monitor real-time MahaRERA extraction jobs"
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

      {/* Grid: Area A (Start New Scrape) & Area B (Current Job) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ======================================================== */}
        {/* AREA A: START NEW SCRAPE (4 Columns)                     */}
        {/* ======================================================== */}
        <div className="lg:col-span-4 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Play size={16} className="text-blue-600" /> Start New Scrape
              </h2>
              {isRunning && (
                <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                  Job In Progress
                </span>
              )}
            </div>

            <form onSubmit={handleStartJob} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-gray-700 mb-1">
                  Target District
                </label>
                <select
                  value={districtName}
                  disabled={isRunning}
                  onChange={(e) => {
                    const sel = PRESET_DISTRICTS.find(
                      (d) => d.name === e.target.value
                    );
                    if (sel) {
                      setDistrictName(sel.name);
                      setDistrictCode(sel.code);
                    }
                  }}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                >
                  {PRESET_DISTRICTS.map((d) => (
                    <option key={d.code} value={d.name}>
                      {d.name} (Code: {d.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    Start Page
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={startPage}
                    disabled={isRunning}
                    onChange={(e) =>
                      setStartPage(Math.max(1, parseInt(e.target.value) || 1))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block font-medium text-gray-700 mb-1">
                    End Page
                  </label>
                  <input
                    type="number"
                    min={startPage}
                    value={endPage}
                    disabled={isRunning}
                    onChange={(e) =>
                      setEndPage(Math.max(startPage, parseInt(e.target.value) || startPage))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg disabled:bg-gray-100"
                  />
                </div>
              </div>

              {/* Advanced Settings Toggle */}
              <div className="pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 font-medium"
                >
                  <Settings size={13} />
                  <span>Advanced Settings</span>
                  {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>

                {showAdvanced && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-3 border border-gray-200/80">
                    <div>
                      <label className="block font-medium text-gray-600 mb-1">
                        Browser Workers (1 or 2)
                      </label>
                      <select
                        value={maxWorkers}
                        disabled={isRunning}
                        onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 1)}
                        className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded-md text-xs"
                      >
                        <option value="1">1 Worker (Recommended for stability)</option>
                        <option value="2">2 Workers (Parallel pages)</option>
                      </select>
                    </div>

                    <label className="flex items-center gap-2 cursor-pointer pt-1">
                      <input
                        type="checkbox"
                        checked={headless}
                        disabled={isRunning}
                        onChange={(e) => setHeadless(e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-gray-700">Run Headless Chrome</span>
                    </label>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || isRunning}
                className="w-full mt-4 py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>Initializing...</span>
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    <span>Launch Scraping Job</span>
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="mt-6 pt-3 border-t border-gray-100 text-[11px] text-gray-400">
            <span>Runs isolated worker process decoupled from backend reloads.</span>
          </div>
        </div>

        {/* ======================================================== */}
        {/* AREA B: CURRENT / SELECTED JOB (8 Columns)              */}
        {/* ======================================================== */}
        <div className="lg:col-span-8 bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
              <div>
                <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                  <Activity size={16} className="text-emerald-600" /> Active Job Status
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Real-time telemetry and extraction counters
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
                </div>
              )}
            </div>

            {activeJob ? (
              <div className="space-y-5">
                {/* Job Metadata Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-gray-50 rounded-xl border border-gray-200/70 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Job Identifier</span>
                    <span className="font-mono font-medium text-gray-800 truncate block">
                      {activeJob.job_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Target District</span>
                    <span className="font-semibold text-gray-800 block">
                      {activeJob.district_name}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Page Scope</span>
                    <span className="font-semibold text-gray-800 block">
                      Page {activeJob.start_page} to {activeJob.end_page - 1}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Started</span>
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
                          ? `Extracting Page ${activeJob.current_page || activeJob.start_page}...`
                          : activeJob.status === "COMPLETED"
                          ? "Extraction completed successfully."
                          : `Job ${activeJob.status.toLowerCase()}`}
                      </span>
                    </span>
                    <span className="font-mono text-gray-500">
                      {calculateProgress()}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-500 ${
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

                {/* 4 Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 bg-white border border-gray-200 rounded-lg text-center">
                    <span className="text-gray-400 text-[10px] uppercase font-bold block">Current Page</span>
                    <span className="text-lg font-bold text-gray-800">
                      {activeJob.current_page || activeJob.start_page} / {activeJob.end_page - 1}
                    </span>
                  </div>
                  <div className="p-3 bg-white border border-gray-200 rounded-lg text-center">
                    <span className="text-gray-400 text-[10px] uppercase font-bold block">Discovered</span>
                    <span className="text-lg font-bold text-gray-800">
                      {activeJob.projects_found || activeJob.projects_extracted || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-white border border-gray-200 rounded-lg text-center">
                    <span className="text-gray-400 text-[10px] uppercase font-bold block">Successful</span>
                    <span className="text-lg font-bold text-emerald-600">
                      {activeJob.projects_extracted || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-white border border-gray-200 rounded-lg text-center">
                    <span className="text-gray-400 text-[10px] uppercase font-bold block">Failed</span>
                    <span className="text-lg font-bold text-red-600">
                      {activeJob.projects_failed || 0}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-gray-400 text-xs">
                No active or selected scraping jobs found.
              </div>
            )}
          </div>

          {/* Collapsible Execution Logs Drawer */}
          {activeJob && (
            <div className="mt-5 pt-4 border-t border-gray-100">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="w-full flex items-center justify-between text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 px-3 py-2 rounded-lg border border-gray-200 transition"
              >
                <span className="flex items-center gap-2">
                  <Terminal size={14} className="text-gray-500" />
                  <span>Execution Diagnostics & Logs ({logs.length} entries)</span>
                </span>
                {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showLogs && (
                <div className="mt-3 bg-gray-900 rounded-lg p-3 text-xs font-mono text-gray-200 h-56 overflow-y-auto space-y-1 shadow-inner">
                  {logs.length === 0 ? (
                    <div className="text-gray-500 italic p-2">Waiting for task execution logs...</div>
                  ) : (
                    logs.map((log, index) => (
                      <div key={index} className="flex gap-2 leading-relaxed">
                        <span className="text-gray-500 shrink-0 text-[10px]">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </span>
                        <span
                          className={`shrink-0 font-bold text-[10px] px-1 rounded ${
                            log.level === "ERROR"
                              ? "bg-red-950 text-red-400"
                              : log.level === "WARNING"
                              ? "bg-amber-950 text-amber-400"
                              : "bg-blue-950 text-blue-400"
                          }`}
                        >
                          {log.level}
                        </span>
                        <span className="text-gray-300 break-all">{log.message}</span>
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ======================================================== */}
      {/* AREA C: RECENT JOB HISTORY                               */}
      {/* ======================================================== */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Recent Job History</h3>
            <p className="text-xs text-gray-500">
              Audit log of completed and running scraping jobs loaded directly from database
            </p>
          </div>
          <span className="text-xs text-gray-500 font-mono">
            {jobs.length} Jobs Recorded
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider font-semibold border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Job Identifier</th>
                <th className="py-3 px-4">District</th>
                <th className="py-3 px-4 text-center">Page Scope</th>
                <th className="py-3 px-4 text-center">Extracted</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4">Started</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-sans">
              {jobs.map((job) => {
                const isSelected = activeJob?.job_id === job.job_id;
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
                      {job.district_name}
                    </td>
                    <td className="py-3 px-4 text-center font-mono text-gray-600">
                      Pages {job.start_page}–{job.end_page - 1}
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-emerald-600">
                      {job.projects_extracted || 0}
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
                            : "danger"
                        }
                      >
                        {job.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono text-gray-500">
                      {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-3 px-4 text-right">
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
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
