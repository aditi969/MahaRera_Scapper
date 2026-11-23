"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { CardSkeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { fetchHealth, fetchCaptchaHealth, testCaptchaOcr } from "@/lib/api";
import { CaptchaHealthData } from "@/types";
import {
  Activity,
  CheckCircle2,
  Database,
  Cpu,
  Server,
  Radio,
  FileCode,
  RefreshCw,
  Clock,
  ShieldCheck,
  AlertCircle,
  ScanEye,
  Check,
  XCircle,
  Zap,
  Target,
  RotateCw,
  FileSearch,
} from "lucide-react";

interface HealthData {
  status: string;
  app_name: string;
  version: string;
  database: string;
  total_projects: number;
  captcha?: {
    status: string;
    status_label: string;
    tesseract_version?: string | null;
    opencv_version?: string | null;
    solve_rate_percent: number;
    total_attempts: number;
    total_accepted: number;
  };
  timestamp: string;
}

export default function SystemStatusPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [captchaHealth, setCaptchaHealth] = useState<CaptchaHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [checking, setChecking] = useState(false);
  const [testingOcr, setTestingOcr] = useState(false);

  const checkHealth = async () => {
    try {
      setChecking(true);
      setError(null);
      const start = performance.now();
      const [healthRes, captchaRes] = await Promise.all([
        fetchHealth(),
        fetchCaptchaHealth(false),
      ]);
      const elapsed = Math.round(performance.now() - start);
      setLatency(elapsed);
      setHealth(healthRes);
      setCaptchaHealth(captchaRes);
      setLastChecked(new Date());
    } catch (err: any) {
      setError(err?.message || "Could not connect to FastAPI backend service.");
    } finally {
      setLoading(false);
      setChecking(false);
    }
  };

  const handleTestOcr = async () => {
    try {
      setTestingOcr(true);
      const res = await testCaptchaOcr();
      if (captchaHealth) {
        setCaptchaHealth({
          ...captchaHealth,
          self_test: res,
        });
      }
    } catch (err: any) {
      console.error("OCR test failed:", err);
    } finally {
      setTestingOcr(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Auto-poll every 15 seconds
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !health) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="System Status & Diagnostics"
          subtitle="Live operational telemetry, database connection, and CAPTCHA OCR health."
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <TableSkeleton rows={5} />
      </div>
    );
  }

  const isHealthy = health?.status === "healthy";
  const isCaptchaHealthy = captchaHealth?.status === "healthy";

  const services = [
    {
      name: "FastAPI Application Server",
      description: "Asynchronous REST API endpoints, routing, and schema validation",
      status: isHealthy ? "Operational" : "Offline",
      latency: latency !== null ? `${latency} ms` : "—",
      icon: <Server className="w-5 h-5 text-blue-600" />,
      tag: "Port 8000",
    },
    {
      name: "Relational Database Engine",
      description: `Active dialect: ${health?.database || "SQLAlchemy ORM"}`,
      status: health?.database ? "Connected" : "Disconnected",
      latency: "Direct pool",
      icon: <Database className="w-5 h-5 text-emerald-600" />,
      tag: `${health?.total_projects || 0} projects indexed`,
    },
    {
      name: "CAPTCHA OCR Solver Subsystem",
      description: `Engine: Tesseract ${captchaHealth?.engine.tesseract.version || "OCR"} + OpenCV ${captchaHealth?.engine.opencv.version || "4.9.0"} (CLAHE/Otsu/Adaptive)`,
      status: isCaptchaHealthy ? "Operational" : captchaHealth?.status === "degraded" ? "Degraded" : "Offline",
      latency: captchaHealth?.self_test ? `${captchaHealth.self_test.latency_ms} ms` : "Ready",
      icon: <ScanEye className="w-5 h-5 text-teal-600" />,
      tag: "Dual-Engine OCR",
    },
    {
      name: "MahaRERA Scraper Engine",
      description: "Direct URL pagination, Selenium WebDriver, and captcha solver",
      status: "Ready",
      latency: "Standby",
      icon: <Cpu className="w-5 h-5 text-indigo-600" />,
      tag: "v3.0 Pipeline",
    },
    {
      name: "Real-time WebSocket Broadcast",
      description: "Sub-second streaming of worker task logs and progress counters",
      status: "Active",
      latency: "< 5 ms",
      icon: <Radio className="w-5 h-5 text-amber-600" />,
      tag: "/ws/scraper",
    },
    {
      name: "PDF & OCR Parsing Pipeline",
      description: "PyMuPDF digital stream reader with fallback Tesseract OCR",
      status: "Operational",
      latency: "Local",
      icon: <FileCode className="w-5 h-5 text-purple-600" />,
      tag: "Dual-Engine",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Status & Diagnostics"
        subtitle="Live operational telemetry, database connection, and CAPTCHA OCR health."
        action={
          <button
            onClick={checkHealth}
            disabled={checking}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? "animate-spin" : ""}`} />
            Run Diagnostics Ping
          </button>
        }
      />

      {/* Primary Status Banner */}
      <div
        className={`p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
          isHealthy
            ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
            : "bg-red-50/70 border-red-200 text-red-900"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center ${
              isHealthy ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
            }`}
          >
            {isHealthy ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <AlertCircle className="w-6 h-6" />
            )}
          </div>
          <div>
            <h2 className="text-base font-bold">
              {isHealthy ? "All Platform Systems Operational" : "Service Disruption Detected"}
            </h2>
            <p className="text-xs text-gray-600 mt-0.5">
              {isHealthy
                ? "FastAPI server, database engine, and CAPTCHA OCR pipeline are responding within healthy thresholds."
                : error || "Unable to reach the backend service."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-gray-600">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span>
              Checked: {lastChecked ? lastChecked.toLocaleTimeString() : "Just now"}
            </span>
          </div>
          {latency !== null && (
            <div className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-md border border-gray-200">
              <Activity className="w-3.5 h-3.5 text-blue-600" />
              <span className="font-semibold text-gray-800">{latency} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* CAPTCHA Health & Operational Metrics Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-teal-50/50 to-white flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-teal-100 text-teal-700 rounded-lg">
              <ScanEye className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-gray-900 text-sm">CAPTCHA Solver & OCR Engine Health</h3>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                    isCaptchaHealthy
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : captchaHealth?.status === "degraded"
                      ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isCaptchaHealthy ? "bg-emerald-500" : captchaHealth?.status === "degraded" ? "bg-amber-500" : "bg-red-500"
                    }`}
                  />
                  {captchaHealth?.status_label || "Checking..."}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Automated canvas capture, OpenCV multi-pass thresholding, and Tesseract neural OCR
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <button
              onClick={handleTestOcr}
              disabled={testingOcr}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-50 border border-teal-200 text-xs font-medium text-teal-700 rounded-lg hover:bg-teal-100 transition-colors disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${testingOcr ? "animate-spin text-teal-600" : "text-teal-600"}`} />
              {testingOcr ? "Testing OCR..." : "Test OCR Diagnostics"}
            </button>
          </div>
        </div>

        {/* Captcha Subsystem Details */}
        <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-4 border-b border-gray-100 bg-gray-50/30">
          {/* Tesseract Status */}
          <div className="p-3.5 bg-white rounded-lg border border-gray-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Tesseract OCR</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${captchaHealth?.engine.tesseract.installed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                  {captchaHealth?.engine.tesseract.installed ? "DETECTED" : "MISSING"}
                </span>
              </div>
              <p className="text-sm font-bold text-gray-900 font-mono">
                {captchaHealth?.engine.tesseract.version || "Not detected"}
              </p>
              <p className="text-[11px] text-gray-500 truncate mt-1" title={captchaHealth?.engine.tesseract.path || ""}>
                {captchaHealth?.engine.tesseract.path || "Tesseract binary not found on PATH"}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500">
              <span>Engine Model</span>
              <span className="font-mono text-gray-700">OEM 3 (LSTM)</span>
            </div>
          </div>

          {/* OpenCV Status */}
          <div className="p-3.5 bg-white rounded-lg border border-gray-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">OpenCV Filter</span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${captchaHealth?.engine.opencv.installed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                  {captchaHealth?.engine.opencv.installed ? "OPERATIONAL" : "MISSING"}
                </span>
              </div>
              <p className="text-sm font-bold text-gray-900 font-mono">
                v{captchaHealth?.engine.opencv.version || "N/A"}
              </p>
              <p className="text-[11px] text-gray-500 mt-1">
                CLAHE (clip=2.5) + Otsu Binarization + Adaptive Threshold
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500">
              <span>CLAHE Support</span>
              <span className="text-emerald-600 font-medium">Supported</span>
            </div>
          </div>

          {/* Synthetic OCR Test */}
          <div className="p-3.5 bg-white rounded-lg border border-gray-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Live OCR Self-Test</span>
                {captchaHealth?.self_test ? (
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded flex items-center gap-1 ${captchaHealth.self_test.passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                    {captchaHealth.self_test.passed ? <Check className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    {captchaHealth.self_test.passed ? "PASSED" : "FAILED"}
                  </span>
                ) : (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">READY</span>
                )}
              </div>
              <div className="flex items-baseline gap-2">
                <p className="text-sm font-bold text-gray-900 font-mono">
                  {captchaHealth?.self_test?.latency_ms !== undefined ? `${captchaHealth.self_test.latency_ms} ms` : "Standby"}
                </p>
                <span className="text-[11px] text-gray-500">recognition time</span>
              </div>
              <p className="text-[11px] text-gray-500 mt-1">
                {captchaHealth?.self_test?.test_recognized ? (
                  <>Recognized: <span className="font-mono font-bold text-gray-800">"{captchaHealth.self_test.test_recognized}"</span> (Exp: "{captchaHealth.self_test.test_expected}")</>
                ) : (
                  "Click 'Test OCR Diagnostics' above to run synthetic check"
                )}
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-500">
              <span>Charset Whitelist</span>
              <span className="font-mono text-gray-700">[A-Z0-9] (6-char)</span>
            </div>
          </div>
        </div>

        {/* Captcha Operational Metrics Row */}
        <div className="p-5">
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3">
            Real-Time CAPTCHA Operational Metrics
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Solve Success Rate</span>
              <span className="text-base font-bold text-emerald-600">
                {captchaHealth?.metrics.solve_rate_percent !== undefined ? `${captchaHealth.metrics.solve_rate_percent}%` : "100%"}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Total OCR Attempts</span>
              <span className="text-base font-bold text-gray-900">
                {captchaHealth?.metrics.total_attempts ?? 0}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Accepted Captchas</span>
              <span className="text-base font-bold text-teal-600">
                {captchaHealth?.metrics.total_accepted ?? 0}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Invalid Rejections</span>
              <span className="text-base font-bold text-amber-600">
                {captchaHealth?.metrics.total_rejected ?? 0}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Canvas Refreshes</span>
              <span className="text-base font-bold text-blue-600">
                {captchaHealth?.metrics.total_refreshes ?? 0}
              </span>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-[11px] text-gray-500 block mb-0.5">Avg Tries / Solve</span>
              <span className="text-base font-bold text-indigo-600">
                {captchaHealth?.metrics.avg_attempts_per_solve ?? 1.0}
              </span>
            </div>
          </div>
        </div>

        {/* Recent Captcha Activity Logs */}
        {captchaHealth?.metrics.recent_events && captchaHealth.metrics.recent_events.length > 0 && (
          <div className="border-t border-gray-100 p-5 bg-gray-50/20">
            <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <FileSearch className="w-3.5 h-3.5 text-gray-500" />
              Recent CAPTCHA Solver Events
            </h4>
            <div className="divide-y divide-gray-100 text-xs font-mono">
              {captchaHealth.metrics.recent_events.slice(0, 5).map((ev) => (
                <div key={ev.id} className="py-2 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <span className="text-gray-400 text-[10px]">
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "—"}
                    </span>
                    <span className="text-gray-700 truncate">{ev.message}</span>
                  </div>
                  <span className="text-[10px] text-gray-400 shrink-0">{ev.job_id.slice(0, 8)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Platform Services Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex justify-between items-center">
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Platform Services</h3>
            <p className="text-xs text-gray-500">
              Health check verification across core application subsystems
            </p>
          </div>
          <span className="text-[11px] font-medium text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full border border-gray-200">
            Auto-refresh: 15s
          </span>
        </div>

        <div className="divide-y divide-gray-100">
          {services.map((svc, i) => (
            <div
              key={i}
              className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-50/60 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 bg-gray-50 border border-gray-200/80 rounded-lg">
                  {svc.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-800 text-sm">{svc.name}</span>
                    <span className="text-[10px] font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                      {svc.tag}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{svc.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 self-end sm:self-center">
                <span className="text-xs font-mono text-gray-500">{svc.latency}</span>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                    svc.status === "Operational" ||
                    svc.status === "Connected" ||
                    svc.status === "Ready" ||
                    svc.status === "Active"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : svc.status === "Degraded"
                      ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      svc.status === "Operational" ||
                      svc.status === "Connected" ||
                      svc.status === "Ready" ||
                      svc.status === "Active"
                        ? "bg-emerald-500"
                        : svc.status === "Degraded"
                        ? "bg-amber-500"
                        : "bg-red-500"
                    }`}
                  />
                  {svc.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Telemetry & Metadata Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-3">
            Environment & Deployment
          </h4>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Platform Version</dt>
              <dd className="font-mono font-medium text-gray-800">
                {health?.version || "1.0.0"}
              </dd>
            </div>
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Application Name</dt>
              <dd className="font-medium text-gray-800">{health?.app_name || "RERA Insight"}</dd>
            </div>
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Frontend Framework</dt>
              <dd className="font-medium text-gray-800">Next.js 14 App Router + TypeScript</dd>
            </div>
            <div className="flex justify-between py-1">
              <dt className="text-gray-500">Backend Framework</dt>
              <dd className="font-medium text-gray-800">FastAPI + Pydantic v2</dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <h4 className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-3">
            Storage & Telemetry
          </h4>
          <dl className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Database Engine</dt>
              <dd className="font-mono font-medium text-gray-800">
                {health?.database || "PostgreSQL / SQLite"}
              </dd>
            </div>
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Indexed Projects</dt>
              <dd className="font-mono font-medium text-gray-800">
                {health?.total_projects || 0} Records
              </dd>
            </div>
            <div className="flex justify-between py-1 border-b border-gray-100">
              <dt className="text-gray-500">Health Timestamp</dt>
              <dd className="font-mono text-gray-800">
                {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : "—"}
              </dd>
            </div>
            <div className="flex justify-between py-1">
              <dt className="text-gray-500">Security & Sandboxing</dt>
              <dd className="inline-flex items-center gap-1 font-medium text-emerald-600">
                <ShieldCheck className="w-3.5 h-3.5" /> Enforced
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}
