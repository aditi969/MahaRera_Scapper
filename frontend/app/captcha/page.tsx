"use client";

import React, { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { CardSkeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { fetchCaptchaHealth, testCaptchaOcr } from "@/lib/api";
import { CaptchaHealthData } from "@/types";
import {
  ScanEye,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Clock,
  Zap,
  Check,
  XCircle,
  FileSearch,
  Cpu,
  Layers,
  ShieldCheck,
  Terminal,
} from "lucide-react";

export default function CaptchaHealthPage() {
  const [captchaHealth, setCaptchaHealth] = useState<CaptchaHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [checking, setChecking] = useState(false);
  const [testingOcr, setTestingOcr] = useState(false);

  const loadData = async (runTest = false) => {
    try {
      setChecking(true);
      setError(null);
      const res = await fetchCaptchaHealth(runTest);
      setCaptchaHealth(res);
      setLastChecked(new Date());
    } catch (err: any) {
      setError(err?.message || "Failed to communicate with CAPTCHA health service.");
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
      console.error("OCR self-test failed:", err);
    } finally {
      setTestingOcr(false);
    }
  };

  useEffect(() => {
    loadData(true);
    const interval = setInterval(() => loadData(false), 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !captchaHealth) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="CAPTCHA Solver Health & Metrics"
          subtitle="Real-time diagnostics of OpenCV image filters, Tesseract neural OCR engine, and live solving telemetry."
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

  const isHealthy = captchaHealth?.status === "healthy";
  const metrics = captchaHealth?.metrics;
  const engine = captchaHealth?.engine;
  const selfTest = captchaHealth?.self_test;

  return (
    <div className="space-y-6">
      <PageHeader
        title="CAPTCHA Solver Health & Metrics"
        subtitle="Real-time diagnostics of OpenCV image filters, Tesseract neural OCR engine, and live solving telemetry."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadData(true)}
              disabled={checking}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 text-xs font-medium text-gray-700 rounded-lg hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checking ? "animate-spin" : ""}`} />
              Refresh Metrics
            </button>
            <button
              onClick={handleTestOcr}
              disabled={testingOcr}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-700 transition-colors shadow-sm disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${testingOcr ? "animate-spin" : ""}`} />
              {testingOcr ? "Executing OCR..." : "Run Live OCR Diagnostics"}
            </button>
          </div>
        }
      />

      {/* Main Status Banner */}
      <div
        className={`p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
          isHealthy
            ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
            : captchaHealth?.status === "degraded"
            ? "bg-amber-50/70 border-amber-200 text-amber-900"
            : "bg-red-50/70 border-red-200 text-red-900"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center ${
              isHealthy
                ? "bg-emerald-100 text-emerald-700"
                : captchaHealth?.status === "degraded"
                ? "bg-amber-100 text-amber-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {isHealthy ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <AlertCircle className="w-6 h-6" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold">
                {isHealthy
                  ? "CAPTCHA OCR Solver Operational"
                  : captchaHealth?.status === "degraded"
                  ? "Degraded OCR Engine Fallback"
                  : "CAPTCHA Subsystem Offline"}
              </h2>
              <span className="text-[11px] font-mono font-semibold bg-white/80 px-2 py-0.5 rounded-full border border-gray-200 text-gray-700">
                {captchaHealth?.status_label}
              </span>
            </div>
            <p className="text-xs text-gray-600 mt-0.5">
              {isHealthy
                ? "OpenCV multi-pass image pre-processor and Tesseract neural OCR engine are verified and ready for MahaRERA scraping."
                : error || "Solver pipeline encountered an issue. Check Tesseract installation on system PATH."}
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
          {selfTest?.latency_ms !== undefined && (
            <div className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-md border border-gray-200">
              <Zap className="w-3.5 h-3.5 text-teal-600" />
              <span className="font-semibold text-gray-800">{selfTest.latency_ms} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Engine Architecture & Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Tesseract OCR Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-blue-50 text-blue-600 rounded-lg">
                  <ScanEye className="w-4 h-4" />
                </div>
                <h3 className="font-semibold text-gray-900 text-sm">Tesseract OCR</h3>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  engine?.tesseract.installed
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-red-50 text-red-700 border border-red-200"
                }`}
              >
                {engine?.tesseract.installed ? "ACTIVE" : "MISSING"}
              </span>
            </div>
            <p className="text-lg font-mono font-bold text-gray-900">
              {engine?.tesseract.version || "Not Detected"}
            </p>
            <p className="text-xs text-gray-500 mt-1 truncate" title={engine?.tesseract.path || ""}>
              Path: {engine?.tesseract.path || "Tesseract binary not found"}
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>Engine Mode</span>
              <span className="font-mono text-gray-800">OEM 3 (Neural LSTM)</span>
            </div>
            <div className="flex justify-between">
              <span>Page Segmentation</span>
              <span className="font-mono text-gray-800">PSM 7 (Single Line)</span>
            </div>
            <div className="flex justify-between">
              <span>Character Filter</span>
              <span className="font-mono text-gray-800">[A-Z0-9] 6-char</span>
            </div>
          </div>
        </div>

        {/* OpenCV Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Layers className="w-4 h-4" />
                </div>
                <h3 className="font-semibold text-gray-900 text-sm">OpenCV Filters</h3>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                  engine?.opencv.installed
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-amber-50 text-amber-700 border border-amber-200"
                }`}
              >
                {engine?.opencv.installed ? "ACTIVE" : "PIL FALLBACK"}
              </span>
            </div>
            <p className="text-lg font-mono font-bold text-gray-900">
              v{engine?.opencv.version || "N/A"}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Multi-pass noise removal, scaling (fx=3.5), & contrast enhancement
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 space-y-1">
            <div className="flex justify-between">
              <span>CLAHE Enhancement</span>
              <span className="text-emerald-600 font-semibold">clipLimit=2.5 (8x8)</span>
            </div>
            <div className="flex justify-between">
              <span>Binarization Passes</span>
              <span className="font-mono text-gray-800">Otsu + Adaptive C</span>
            </div>
            <div className="flex justify-between">
              <span>Candidate Sorter</span>
              <span className="font-mono text-gray-800">Length penalty scoring</span>
            </div>
          </div>
        </div>

        {/* Synthetic OCR Self-Test Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-teal-50 text-teal-600 rounded-lg">
                  <Zap className="w-4 h-4" />
                </div>
                <h3 className="font-semibold text-gray-900 text-sm">Live OCR Test</h3>
              </div>
              {selfTest ? (
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                    selfTest.passed
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  {selfTest.passed ? <Check className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                  {selfTest.passed ? "PASSED" : "FAILED"}
                </span>
              ) : (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  READY
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-lg font-mono font-bold text-gray-900">
                {selfTest?.latency_ms !== undefined ? `${selfTest.latency_ms} ms` : "Standby"}
              </p>
              <span className="text-xs text-gray-500">end-to-end latency</span>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {selfTest?.test_recognized ? (
                <>
                  Recognized: <span className="font-mono font-bold text-gray-900">"{selfTest.test_recognized}"</span> (Expected: "{selfTest.test_expected}")
                </>
              ) : (
                "Click 'Run Live OCR Diagnostics' to test synthetic captcha."
              )}
            </p>
          </div>

          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
            <span className="text-gray-500">Synthetic Target</span>
            <span className="font-mono text-gray-800">Dynamic In-Memory</span>
          </div>
        </div>
      </div>

      {/* Operational Metrics Cards */}
      <div>
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-3">
          CAPTCHA Engine Operational Metrics (All Jobs)
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Solve Success Rate</span>
            <span className="text-2xl font-bold text-emerald-600">
              {metrics?.solve_rate_percent !== undefined ? `${metrics.solve_rate_percent}%` : "100%"}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Accepted vs Blocked</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Total OCR Attempts</span>
            <span className="text-2xl font-bold text-gray-900">
              {metrics?.total_attempts ?? 0}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Inference passes</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Accepted Captchas</span>
            <span className="text-2xl font-bold text-teal-600">
              {metrics?.total_accepted ?? 0}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Verified on MahaRERA</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Invalid Rejections</span>
            <span className="text-2xl font-bold text-amber-600">
              {metrics?.total_rejected ?? 0}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Auto-retried by scraper</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Canvas Refreshes</span>
            <span className="text-2xl font-bold text-blue-600">
              {metrics?.total_refreshes ?? 0}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Page reloads on retry</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <span className="text-[11px] font-medium text-gray-500 block mb-1">Avg Tries / Solve</span>
            <span className="text-2xl font-bold text-indigo-600">
              {metrics?.avg_attempts_per_solve ?? 1.0}
            </span>
            <span className="text-[10px] text-gray-400 block mt-1">Attempts per success</span>
          </div>
        </div>
      </div>

      {/* Solver Lifecycle & How It Works */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h3 className="text-xs font-semibold text-gray-900 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Terminal className="w-4 h-4 text-blue-600" />
          MahaRERA CAPTCHA Solver Architecture & Lifecycle
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <span className="font-semibold text-gray-900 block mb-1">1. Canvas Capture</span>
            <p className="text-gray-600">
              Captures <code className="bg-gray-200 px-1 py-0.5 rounded text-[11px]">#captcahCanvas</code> directly via <code className="bg-gray-200 px-1 py-0.5 rounded text-[11px]">toDataURL('image/png')</code> in JavaScript with element screenshot fallback.
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <span className="font-semibold text-gray-900 block mb-1">2. OpenCV Pre-Processing</span>
            <p className="text-gray-600">
              Adds border padding, applies 3.5x cubic interpolation, CLAHE (clip=2.5), Otsu binarization, and adaptive Gaussian thresholding.
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <span className="font-semibold text-gray-900 block mb-1">3. Tesseract Neural OCR</span>
            <p className="text-gray-600">
              Executes LSTM engine with single-line PSM 7 and strict alphanumeric whitelist <code className="bg-gray-200 px-1 py-0.5 rounded text-[11px]">[A-Z0-9]</code>.
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
            <span className="font-semibold text-gray-900 block mb-1">4. Auto-Retry & Recovery</span>
            <p className="text-gray-600">
              Detects "Invalid Captcha" modal, automatically dismisses popup, refreshes canvas up to 3 bounded rounds to prevent blocking.
            </p>
          </div>
        </div>
      </div>

      {/* Recent CAPTCHA Activity Feed */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSearch className="w-4 h-4 text-gray-600" />
            <h3 className="font-semibold text-gray-900 text-sm">Recent CAPTCHA Activity Logs</h3>
          </div>
          <span className="text-xs text-gray-500 font-mono">
            Source: PostgreSQL <code className="bg-gray-100 px-1 py-0.5 rounded">scrape_logs</code>
          </span>
        </div>

        {metrics?.recent_events && metrics.recent_events.length > 0 ? (
          <div className="divide-y divide-gray-100 text-xs font-mono">
            {metrics.recent_events.map((ev) => (
              <div key={ev.id} className="p-3 flex items-center justify-between gap-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-3 truncate">
                  <span className="text-gray-400 text-[11px] shrink-0">
                    {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-semibold shrink-0 ${
                      ev.message.includes("✅")
                        ? "bg-emerald-100 text-emerald-800"
                        : ev.message.includes("❌")
                        ? "bg-amber-100 text-amber-800"
                        : ev.message.includes("🚫")
                        ? "bg-red-100 text-red-800"
                        : "bg-blue-100 text-blue-800"
                    }`}
                  >
                    {ev.level}
                  </span>
                  <span className="text-gray-800 truncate">{ev.message}</span>
                </div>
                <span className="text-[11px] text-gray-400 shrink-0 font-mono">
                  Job: {ev.job_id.slice(0, 8)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-gray-500">
            <ScanEye className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="font-medium text-gray-700">No CAPTCHA logs recorded yet.</p>
            <p className="text-gray-400 mt-0.5">
              Launch a scrape job from <a href="/scraper" className="text-blue-600 hover:underline">Scraper Control</a> to see live solver telemetry.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
