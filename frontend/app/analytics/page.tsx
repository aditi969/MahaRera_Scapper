"use client";

import React, { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { BarChart3, TrendingUp, Calendar, Layers, PieChart as PieIcon } from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { ErrorState } from "../../components/ui/ErrorState";
import {
  fetchDistricts,
  fetchStatusStats,
  fetchProjectTypes,
  fetchRegistrationTrend,
  fetchCompletionTrend,
} from "../../lib/api";
import {
  CompletionPoint,
  DistrictStat,
  ProjectTypeStat,
  StatusStat,
  TrendPoint,
} from "../../types";

const PIE_COLORS = ["#2563EB", "#16A34A", "#D97706", "#7C3AED", "#0891B2", "#DC2626"];

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [districts, setDistricts] = useState<DistrictStat[]>([]);
  const [statuses, setStatuses] = useState<StatusStat[]>([]);
  const [projectTypes, setProjectTypes] = useState<ProjectTypeStat[]>([]);
  const [regTrend, setRegTrend] = useState<TrendPoint[]>([]);
  const [compTrend, setCompTrend] = useState<CompletionPoint[]>([]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dist, st, pt, reg, comp] = await Promise.all([
        fetchDistricts(),
        fetchStatusStats(),
        fetchProjectTypes(),
        fetchRegistrationTrend(),
        fetchCompletionTrend(),
      ]);
      setDistricts(dist);
      setStatuses(st);
      setProjectTypes(pt);
      setRegTrend(reg);
      setCompTrend(comp);
    } catch (err: any) {
      setError(err?.message || "Failed to load analytics.");
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
        <PageHeader title="Analytics" subtitle="Real aggregate intelligence" />
        <ErrorState message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics & Market Intelligence"
        subtitle="Calculated strictly from verified stored records in PostgreSQL"
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Analytics" }]}
      />

      {/* Top Row: Registration Trend & Completion Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Registration Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <TrendingUp size={16} className="text-blue-600" /> Registration Velocity
              </h2>
              <p className="text-xs text-gray-400">Monthly new project registrations</p>
            </div>
          </div>
          <div className="h-64">
            {loading ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">Loading...</div>
            ) : regTrend.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">No trend data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={regTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="period" tick={{ fontSize: 11, fill: "#6B7280" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E5E7EB" }}
                    formatter={(v: any) => [`${v} projects`, "Registrations"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCount)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Project Completion Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Calendar size={16} className="text-emerald-600" /> Completion Timeline
              </h2>
              <p className="text-xs text-gray-400">Project delivery schedule by year</p>
            </div>
          </div>
          <div className="h-64">
            {loading ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">Loading...</div>
            ) : compTrend.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-400">No completion schedule data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#6B7280" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#6B7280" }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#E5E7EB" }}
                    formatter={(v: any) => [`${v} projects`, "Scheduled Deliveries"]}
                  />
                  <Bar dataKey="count" fill="#16A34A" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Middle Row: District Comparison, Status Pie, Project Types */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* District Comparison */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-2">
            <Layers size={16} className="text-purple-600" /> District Distribution
          </h2>
          <p className="text-xs text-gray-400 mb-4">Volume per district</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={districts} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="district" type="category" width={80} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(v: any) => [`${v} projects`, "Count"]}
                />
                <Bar dataKey="count" fill="#7C3AED" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-2">
            <PieIcon size={16} className="text-blue-600" /> Status Breakdown
          </h2>
          <p className="text-xs text-gray-400 mb-4">Active vs Completed ratio</p>
          <div className="h-56 flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height={150}>
              <PieChart>
                <Pie
                  data={statuses}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  innerRadius={35}
                >
                  {statuses.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap justify-center gap-3 text-xs mt-2">
              {statuses.map((s, i) => (
                <div key={s.status} className="flex items-center gap-1.5 text-gray-600">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                  />
                  <span>{s.status}</span>
                  <span className="font-semibold text-gray-900">({s.count})</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Project Types */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-900 mb-1 flex items-center gap-2">
            <BarChart3 size={16} className="text-cyan-600" /> Project Typologies
          </h2>
          <p className="text-xs text-gray-400 mb-4">Residential vs Commercial vs Plotted</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={projectTypes} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="project_type" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={(v: any) => [`${v} projects`, "Count"]}
                />
                <Bar dataKey="count" fill="#0891B2" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

