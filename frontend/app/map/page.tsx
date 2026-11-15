"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Filter, MapPin, RefreshCw } from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { FilterSelect } from "../../components/ui/FilterSelect";
import { ErrorState } from "../../components/ui/ErrorState";
import { fetchMapLocations } from "../../lib/api";
import { MapProject } from "../../types";

const FullMap = dynamic(
  () => import("../../components/map/FullMaharashtraMap"),
  {
    ssr: false,
    loading: () => (
      <div className="h-full w-full bg-gray-100 flex items-center justify-center text-xs text-gray-400 animate-pulse">
        Initializing Maharashtra Geospatial Map Layer...
      </div>
    ),
  }
);

const DISTRICT_OPTIONS = [
  { label: "Raigarh", value: "Raigarh" },
  { label: "Mumbai City", value: "Mumbai City" },
  { label: "Mumbai Suburban", value: "Mumbai Suburban" },
  { label: "Thane", value: "Thane" },
  { label: "Pune", value: "Pune" },
];

const STATUS_OPTIONS = [
  { label: "Active", value: "Active" },
  { label: "Completed", value: "Completed" },
];

export default function InteractiveMapPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [projects, setProjects] = useState<MapProject[]>([]);
  const [district, setDistrict] = useState("");
  const [status, setStatus] = useState("");

  const loadMarkers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMapLocations({
        district: district || undefined,
        status: status || undefined,
      });
      setProjects(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load project map locations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMarkers();
  }, [district, status]);

  return (
    <div className="space-y-4 h-[calc(100vh-5rem)] flex flex-col">
      <PageHeader
        title="Interactive Project Map"
        subtitle="Geographic visualization of valid MahaRERA project coordinates"
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Map" }]}
        action={
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md border border-blue-200">
              {projects.length} Pin{projects.length === 1 ? "" : "s"} Displayed
            </span>
            <button
              onClick={loadMarkers}
              className="p-1.5 text-gray-500 hover:text-gray-900 bg-white border border-gray-200 rounded-md transition"
              title="Refresh coordinates"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        }
      />

      {/* Filter Ribbon & Legend */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter size={14} className="text-gray-400" />
          <FilterSelect
            value={district}
            onChange={setDistrict}
            options={DISTRICT_OPTIONS}
            placeholder="All Districts"
            className="w-40 text-xs py-1.5"
          />
          <FilterSelect
            value={status}
            onChange={setStatus}
            options={STATUS_OPTIONS}
            placeholder="All Statuses"
            className="w-36 text-xs py-1.5"
          />
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-blue-600 inline-block" />
            <span>Active / Ongoing</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-emerald-600 inline-block" />
            <span>Completed</span>
          </div>
        </div>
      </div>

      {/* Map View Container */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm relative min-h-[400px]">
        {error ? (
          <div className="p-8">
            <ErrorState message={error} onRetry={loadMarkers} />
          </div>
        ) : (
          <FullMap projects={projects} />
        )}
      </div>
    </div>
  );
}

