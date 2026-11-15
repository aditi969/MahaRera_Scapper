"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import {
  Building2,
  Calendar,
  MapPin,
  ExternalLink,
  ShieldCheck,
  Landmark,
  FileText,
  AlertTriangle,
  ArrowLeft,
  Briefcase,
  Layers,
} from "lucide-react";

import { PageHeader } from "../../../components/layout/PageHeader";
import { Badge } from "../../../components/ui/Badge";
import { Skeleton } from "../../../components/ui/LoadingSkeleton";
import { ErrorState } from "../../../components/ui/ErrorState";
import { fetchProject } from "../../../lib/api";
import { ProjectDetail } from "../../../types";

// Dynamic import Leaflet map with SSR disabled
const ProjectMap = dynamic(
  () => import("../../../components/map/SingleProjectMap"),
  {
    ssr: false,
    loading: () => (
      <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center text-xs text-gray-400 animate-pulse">
        Loading project geospatial location...
      </div>
    ),
  }
);

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reraId = params?.reraId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);

  const loadData = async () => {
    if (!reraId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProject(reraId);
      setProject(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load project details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [reraId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-48 md:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Project Details"
          breadcrumbs={[
            { label: "Home", href: "/" },
            { label: "Projects", href: "/projects" },
            { label: reraId },
          ]}
        />
        <ErrorState message={error || "Project not found"} onRetry={loadData} />
      </div>
    );
  }

  const hasCoords = project.latitude !== null && project.longitude !== null;

  return (
    <div className="space-y-6">
      {/* Back Button & Breadcrumb Header */}
      <div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-900 transition mb-3"
        >
          <ArrowLeft size={14} /> Back to Explorer
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-gray-200 pb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {project.rera_id}
              </span>
              <Badge
                variant={
                  project.project_status?.toLowerCase().includes("active")
                    ? "primary"
                    : project.project_status?.toLowerCase().includes("completed")
                    ? "success"
                    : "neutral"
                }
              >
                {project.project_status || "Unknown Status"}
              </Badge>
              {project.validation_status && (
                <Badge
                  variant={
                    project.validation_status === "VALID"
                      ? "success"
                      : project.validation_status === "PARTIAL"
                      ? "warning"
                      : "danger"
                  }
                >
                  {project.validation_status}
                </Badge>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              {project.project_name || "Unnamed Project"}
            </h1>
            <p className="mt-1 text-xs text-gray-500 flex items-center gap-1.5">
              <MapPin size={13} className="text-gray-400" />
              <span>
                {project.locality ? `${project.locality}, ` : ""}
                {project.taluka ? `${project.taluka}, ` : ""}
                {project.district || "Maharashtra"}
                {project.pin_code ? ` - ${project.pin_code}` : ""}
              </span>
            </p>
          </div>

          {project.source_url && (
            <a
              href={project.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition shadow-sm"
            >
              <ExternalLink size={14} /> MahaRERA Portal Record
            </a>
          )}
        </div>
      </div>

      {/* Grid: Overview & Location Map */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: General & Registration Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* General Information Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Building2 size={16} className="text-blue-600" /> Registration & General Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-gray-400 font-medium">Project Type</span>
                <p className="font-semibold text-gray-800 mt-0.5">{project.project_type || "—"}</p>
              </div>
              <div>
                <span className="text-gray-400 font-medium">Date of Registration</span>
                <p className="font-semibold text-gray-800 mt-0.5">
                  {project.date_of_registration || "—"}
                </p>
              </div>
              <div>
                <span className="text-gray-400 font-medium">Original Completion Date</span>
                <p className="font-semibold text-gray-800 mt-0.5">
                  {project.project_completion_date_original || "—"}
                </p>
              </div>
              <div>
                <span className="text-gray-400 font-medium">Revised Completion Date</span>
                <p className="font-semibold text-gray-800 mt-0.5">
                  {project.project_completion_date_revised || "—"}
                </p>
              </div>
              <div>
                <span className="text-gray-400 font-medium">Organization / Entity</span>
                <p className="font-semibold text-gray-800 mt-0.5">{project.organization || "—"}</p>
              </div>
              <div>
                <span className="text-gray-400 font-medium">Survey Number</span>
                <p className="font-semibold text-gray-800 mt-0.5">{project.survey_no || "—"}</p>
              </div>
            </div>

            {project.project_location && (
              <div className="mt-4 pt-3 border-t border-gray-100 text-xs">
                <span className="text-gray-400 font-medium">Detailed Location Address</span>
                <p className="text-gray-700 mt-0.5 leading-relaxed">{project.project_location}</p>
              </div>
            )}
          </div>

          {/* Certificate Dates Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FileText size={16} className="text-purple-600" /> RERA Certificate & Validity
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs bg-purple-50/50 p-4 rounded-lg border border-purple-100">
              <div>
                <span className="text-purple-700 font-medium">Commencing From</span>
                <p className="font-bold text-gray-900 text-sm mt-0.5">
                  {project.commencing_from || "—"}
                </p>
              </div>
              <div>
                <span className="text-purple-700 font-medium">Dated (Leftmost)</span>
                <p className="font-bold text-gray-900 text-sm mt-0.5">
                  {project.leftmost_date || "—"}
                </p>
              </div>
              <div>
                <span className="text-purple-700 font-medium">Ending With</span>
                <p className="font-bold text-gray-900 text-sm mt-0.5">
                  {project.ending_with || "—"}
                </p>
              </div>
            </div>
            {project.cert_date_source && (
              <div className="mt-3 text-[11px] text-gray-500 font-mono">
                Extraction Provenance: {project.cert_date_source}
              </div>
            )}
          </div>

          {/* Promoter & Legal Details */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Briefcase size={16} className="text-emerald-600" /> Promoter & Legal Information
            </h2>
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-gray-400 font-medium">Promoter Details</span>
                <p className="font-semibold text-gray-800 mt-0.5">
                  {project.promoter_details || "—"}
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-400 font-medium">Outside Investors</span>
                  <p className="font-semibold text-gray-800 mt-0.5">
                    {project.has_investors || "No"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-400 font-medium">Promoter Past Experience</span>
                  <p className="font-semibold text-gray-800 mt-0.5">
                    {project.past_experience_info || "—"}
                  </p>
                </div>
              </div>
              {project.litigations && (
                <div className="pt-2 border-t border-gray-100">
                  <span className="text-gray-400 font-medium">Litigations</span>
                  <p className="text-gray-700 mt-0.5 leading-relaxed">{project.litigations}</p>
                </div>
              )}
            </div>
          </div>

          {/* Building Structures Table (if present) */}
          {project.building_details &&
            project.building_details["Identification of Building"] && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h2 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Layers size={16} className="text-blue-600" /> Sanctioned Buildings & Wings
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-gray-50 text-gray-500 border-b border-gray-100">
                      <tr>
                        <th className="py-2 px-3">Building / Wing Name</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 text-gray-800">
                      {project.building_details["Identification of Building"].map(
                        (b: string, i: number) => (
                          <tr key={i}>
                            <td className="py-2 px-3 font-medium">{b}</td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
        </div>

        {/* Right Column: Geospatial Map, Bank, and Quality */}
        <div className="space-y-6">
          {/* Geospatial Map */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <MapPin size={16} className="text-red-500" /> Project Geospatial Location
            </h2>
            {hasCoords ? (
              <div>
                <div className="h-64 rounded-lg overflow-hidden border border-gray-200">
                  <ProjectMap
                    latitude={project.latitude!}
                    longitude={project.longitude!}
                    projectName={project.project_name || project.rera_id}
                  />
                </div>
                <div className="mt-3 flex justify-between text-[11px] text-gray-500 font-mono">
                  <span>Lat: {project.latitude?.toFixed(4)}</span>
                  <span>Lon: {project.longitude?.toFixed(4)}</span>
                </div>
              </div>
            ) : (
              <div className="h-48 bg-gray-50 rounded-lg border border-dashed border-gray-200 flex flex-col items-center justify-center p-4 text-center">
                <AlertTriangle size={20} className="text-amber-500 mb-2" />
                <span className="text-xs font-semibold text-gray-700">No Geotagged Coordinates</span>
                <p className="text-[11px] text-gray-400 mt-1">
                  MahaRERA submission did not contain valid latitude/longitude coordinates for this record.
                </p>
              </div>
            )}
          </div>

          {/* Designated RERA Bank Account */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <Landmark size={16} className="text-gray-700" /> Designated Bank Account
            </h2>
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-gray-400">Bank Name</span>
                <p className="font-semibold text-gray-800">{project.bank_name || "—"}</p>
              </div>
              <div>
                <span className="text-gray-400">IFSC Code</span>
                <p className="font-mono font-medium text-gray-800">{project.ifsc_code || "—"}</p>
              </div>
              <div>
                <span className="text-gray-400">Branch Address</span>
                <p className="text-gray-700">{project.bank_address || "—"}</p>
              </div>
            </div>
          </div>

          {/* Audit & Quality Details */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-600" /> Data Integrity & Provenance
            </h2>
            <div className="space-y-2 text-xs text-gray-600">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span>Validation Result</span>
                <span className="font-semibold text-gray-900">{project.validation_status}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span>Certificate Status</span>
                <span className="font-semibold text-gray-900">
                  {project.cert_extraction_status || "not_attempted"}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span>Scraped At</span>
                <span className="text-gray-500">{project.scraped_at ? project.scraped_at.slice(0, 19).replace("T", " ") : "—"}</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Last Updated</span>
                <span className="text-gray-500">{project.updated_at ? project.updated_at.slice(0, 19).replace("T", " ") : "—"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

