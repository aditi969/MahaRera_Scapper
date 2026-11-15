"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpDown, RotateCcw, Building2 } from "lucide-react";

import { PageHeader } from "../../components/layout/PageHeader";
import { SearchInput } from "../../components/ui/SearchInput";
import { FilterSelect } from "../../components/ui/FilterSelect";
import { Pagination } from "../../components/ui/Pagination";
import { Badge } from "../../components/ui/Badge";
import { TableSkeleton } from "../../components/ui/LoadingSkeleton";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { fetchProjects } from "../../lib/api";
import { ProjectListItem, ProjectListResponse } from "../../types";

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
  { label: "Other", value: "Other" },
];

export default function ProjectExplorerPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [projectsData, setProjectsData] = useState<ProjectListResponse | null>(null);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [district, setDistrict] = useState("");
  const [status, setStatus] = useState("");
  const [sortBy, setSortBy] = useState("date_of_registration");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjects({
        page,
        pageSize,
        search,
        district,
        status,
        sortBy,
        sortDir,
      });
      setProjectsData(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load project listings.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, [page, pageSize, search, district, status, sortBy, sortDir]);

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
    setPage(1);
  };

  const clearFilters = () => {
    setSearch("");
    setDistrict("");
    setStatus("");
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Project Explorer"
        subtitle="Search, filter, and inspect verified Maharashtra RERA registered projects"
        breadcrumbs={[{ label: "Home", href: "/" }, { label: "Projects" }]}
      />

      {/* Filter Row */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="flex-1 w-full flex flex-col sm:flex-row gap-3 items-center">
          <SearchInput
            value={search}
            onChange={(val) => {
              setSearch(val);
              setPage(1);
            }}
            placeholder="Search by project name, RERA ID, or promoter..."
          />
          <FilterSelect
            value={district}
            onChange={(val) => {
              setDistrict(val);
              setPage(1);
            }}
            options={DISTRICT_OPTIONS}
            placeholder="All Districts"
            className="w-full sm:w-44"
          />
          <FilterSelect
            value={status}
            onChange={(val) => {
              setStatus(val);
              setPage(1);
            }}
            options={STATUS_OPTIONS}
            placeholder="All Statuses"
            className="w-full sm:w-36"
          />
        </div>

        {(search || district || status) && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
          >
            <RotateCcw size={13} /> Reset
          </button>
        )}
      </div>

      {/* Main Table Card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <TableSkeleton rows={8} />
        ) : error ? (
          <div className="p-8">
            <ErrorState message={error} onRetry={loadProjects} />
          </div>
        ) : !projectsData || projectsData.data.length === 0 ? (
          <div className="p-12">
            <EmptyState
              title="No projects found"
              description="No registered projects match your search query or filter criteria."
              action={
                search || district || status
                  ? { label: "Clear Filters", onClick: clearFilters }
                  : undefined
              }
            />
          </div>
        ) : (
          <div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-50 text-gray-500 font-semibold border-b border-gray-200 uppercase tracking-wider">
                  <tr>
                    <th
                      onClick={() => handleSort("rera_id")}
                      className="py-3 px-4 cursor-pointer hover:text-gray-900 transition"
                    >
                      <div className="flex items-center gap-1">
                        <span>RERA ID</span>
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort("project_name")}
                      className="py-3 px-4 cursor-pointer hover:text-gray-900 transition"
                    >
                      <div className="flex items-center gap-1">
                        <span>Project Name</span>
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort("district")}
                      className="py-3 px-4 cursor-pointer hover:text-gray-900 transition"
                    >
                      <div className="flex items-center gap-1">
                        <span>District</span>
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort("project_status")}
                      className="py-3 px-4 cursor-pointer hover:text-gray-900 transition"
                    >
                      <div className="flex items-center gap-1">
                        <span>Status</span>
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort("date_of_registration")}
                      className="py-3 px-4 cursor-pointer hover:text-gray-900 transition"
                    >
                      <div className="flex items-center gap-1">
                        <span>Reg. Date</span>
                        <ArrowUpDown size={12} />
                      </div>
                    </th>
                    <th className="py-3 px-4">Completion Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-gray-700">
                  {projectsData.data.map((p) => {
                    const compDate =
                      p.project_completion_date_revised ||
                      p.project_completion_date_original ||
                      "—";
                    return (
                      <tr
                        key={p.rera_id}
                        onClick={() => router.push(`/projects/${p.rera_id}`)}
                        className="hover:bg-blue-50/50 transition cursor-pointer"
                      >
                        <td className="py-3 px-4 font-mono font-semibold text-blue-600">
                          {p.rera_id}
                        </td>
                        <td className="py-3 px-4 font-medium text-gray-900 max-w-sm">
                          <div className="truncate font-semibold">{p.project_name || "—"}</div>
                          {p.promoter_details && (
                            <div className="text-[11px] text-gray-400 truncate mt-0.5">
                              {p.promoter_details}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">{p.district || "—"}</td>
                        <td className="py-3 px-4">
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
                        <td className="py-3 px-4 text-gray-500">
                          {p.date_of_registration || "—"}
                        </td>
                        <td className="py-3 px-4 text-gray-500">{compDate}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <Pagination
              currentPage={projectsData.page}
              totalPages={projectsData.total_pages}
              totalItems={projectsData.total}
              pageSize={projectsData.page_size}
              onPageChange={(newPage) => setPage(newPage)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

