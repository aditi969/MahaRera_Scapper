"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  CheckCircle2,
  Clock,
  MapPin,
  ArrowRight,
  TrendingUp,
  ShieldAlert,
  Activity,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts";

import { PageHeader } from "../components/layout/PageHeader";
import { StatCard } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import { CardSkeleton, TableSkeleton } from "../components/ui/LoadingSkeleton";
import { ErrorState } from "../components/ui/ErrorState";
import {
  fetchOverview,
  fetchDistricts,
  fetchStatusStats,
  fetchRegistrationTrend,
  fetchProjects,
  fetchDataQuality,
} from "../lib/api";
import {
  DistrictStat,
  OverviewKPIs,
  ProjectListItem,
  StatusStat,
  TrendPoint,
  DataQualityMetrics,
} from "../types";

const STATUS_COLORS: Record<string, string> = {
  Active: "#2563EB",
  Completed: "#16A34A",
  Lapsed: "#D97706",
  "De-Registered": "#DC2626",
  Other: "#6B7280",
};

export default function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<OverviewKPIs | null>(null);
  const [districts, setDistricts] = useState<DistrictStat[]>([]);
  const [statusStats, setStatusStats] = useState<StatusStat[]>([]);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [recentProjects, setRecentProjects] = useState<ProjectListItem[]>([]);
  const [quality, setQuality] = useState<DataQualityMetrics | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, dist, st, tr, pr, dq] = await Promise.all([
        fetchOverview(),
        fetchDistricts(),
        fetchStatusStats(),
        fetchRegistrationTrend(),
        fetchProjects({ page: 1, pageSize: 6, sortBy: "date_of_registration", sortDir: "desc" }),
        fetchDataQuality(),
      ]);
      setOverview(ov);
      setDistricts(dist);
      setStatusStats(st);
      setTrends(tr);
      setRecentProjects(pr.data);
      setQuality(dq);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard data from backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Overview"
          subtitle="Real-time Maharashtra RERA data intelligence metrics"
        />
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        subtitle="Maharashtra Real Estate Regulatory Authority (MahaRERA) Data Intelligence"
        action={
          <Link
            href="/scraper"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition shadow-sm"
          >
            <Activity size={14} /> Scraper Control
          </Link>
        }
      />

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Projects"
            value={overview?.total_projects || 0}
            subtitle="Verified MahaRERA records in DB"
            icon={<Building2 size={20} />}
          />
          <StatCard
            title="Active Projects"
            value={overview?.active_projects || 0}
            subtitle="Under construction / Ongoing"
            icon={<Clock size={20} />}
            badge={{ text: "Active", variant: "primary" }}
          />
          <StatCard
            title="Completed Projects"
            value={overview?.completed_projects || 0}
            subtitle="Occupancy / Finished"
            icon={<CheckCircle2 size={20} />}
            badge={{ text: "Completed", variant: "success" }}
          />
          <StatCard
            title="Districts Covered"
            value={overview?.total_districts || 0}
            subtitle="Across Maharashtra state"
            icon={<MapPin size={20} />}
          />
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* District Distribution */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-gray-900">District Distribution</h2>
              <p className="text-xs text-gray-400">Total registered projects by district</p>
            </div>
            <Link
              href="/analytics"
              className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
            >
              Analytics <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <span className="text-xs text-gray-400 animate-pulse">Loading chart...</span>
            </div>
          ) : districts.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-xs text-gray-400">
              No district records stored yet.
            </div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={districts} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="district" type="category" width={90} tick={{ fontSize: 11, fill: "#4B5563" }} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E5E7EB" }}
                    formatter={(val: any) => [`${val} projects`, "Count"]}
                  />
                  <Bar dataKey="count" fill="#2563EB" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Status Breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-gray-900">Project Status</h2>
              <p className="text-xs text-gray-400">Classification distribution</p>
            </div>
          </div>
          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <span className="text-xs text-gray-400 animate-pulse">Loading chart...</span>
            </div>
          ) : statusStats.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-xs text-gray-400">
              No status records stored yet.
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center">
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie
                    data={statusStats}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={4}
                  >
                    {statusStats.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={STATUS_COLORS[entry.status || ""] || "#3B82F6"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E5E7EB" }}
                    formatter={(val: any) => [`${val} projects`, "Count"]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap justify-center gap-3 mt-2 text-xs">
                {statusStats.map((s) => (
                  <div key={s.status} className="flex items-center gap-1.5 text-gray-600">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[s.status || ""] || "#3B82F6" }}
                    />
                    <span>{s.status}</span>
                    <span className="font-semibold text-gray-900">({s.count})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Grid: Recent Projects & Data Quality Widget */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Projects Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="flex items-center justify-between p-5 border-b border-gray-100">
            <div>
              <h2 className="text-sm font-bold text-gray-900">Recently Scraped Projects</h2>
              <p className="text-xs text-gray-400">Latest records ingested into PostgreSQL</p>
            </div>
            <Link
              href="/projects"
              className="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1"
            >
              View Explorer <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? (
            <TableSkeleton rows={4} />
          ) : recentProjects.length === 0 ? (
            <div className="p-8 text-center text-xs text-gray-400">No projects stored.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 text-gray-500 font-semibold border-b border-gray-100">
                  <tr>
                    <th className="py-2.5 px-4">RERA ID</th>
                    <th className="py-2.5 px-4">Project Name</th>
                    <th className="py-2.5 px-4">District</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Registration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-gray-700">
                  {recentProjects.map((p) => (
                    <tr
                      key={p.rera_id}
                      className="hover:bg-gray-50 transition cursor-pointer"
                    >
                      <td className="py-2.5 px-4 font-mono font-medium text-blue-600">
                        <Link href={`/projects/${p.rera_id}`}>{p.rera_id}</Link>
                      </td>
                      <td className="py-2.5 px-4 font-medium text-gray-900 max-w-xs truncate">
                        {p.project_name || "—"}
                      </td>
                      <td className="py-2.5 px-4">{p.district || "—"}</td>
                      <td className="py-2.5 px-4">
                        <Badge
                          variant={
                            p.project_status?.toLowerCase().includes("active")
                              ? "primary"
                              : p.project_status?.toLowerCase().includes("completed")
                              ? "success"
                              : "neutral"
                          }
                        >
                          {p.project_status || "Unknown"}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4 text-gray-500">
                        {p.date_of_registration || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Data Quality Health Widget */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Data Trust Score</h2>
                <p className="text-xs text-gray-400">Ingestion validity & completeness</p>
              </div>
              <Link
                href="/data-quality"
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Inspect
              </Link>
            </div>
            {quality && (
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100 text-center">
                  <span className="text-3xl font-extrabold text-blue-700">
                    {quality.completeness_score}%
                  </span>
                  <p className="text-xs text-blue-600 font-medium mt-1">Field Completeness</p>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Valid RERA ID Format</span>
                    <span className="font-semibold text-emerald-600">
                      {quality.valid_rera_ids}/{quality.total_records}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Geospatial Coordinates</span>
                    <span className="font-semibold text-gray-800">
                      {quality.records_with_coordinates}/{quality.total_records}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">Certificate PDF Dates</span>
                    <span className="font-semibold text-gray-800">
                      {quality.cert_extraction_rate}%
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-gray-500">Duplicates Detected</span>
                    <span className="font-semibold text-gray-800">
                      {quality.duplicate_count}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
          <Link
            href="/data-quality"
            className="mt-4 block w-full text-center py-2 text-xs font-semibold text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition"
          >
            Review Data Quality Reports
          </Link>
        </div>
      </div>
    </div>
  );
}

