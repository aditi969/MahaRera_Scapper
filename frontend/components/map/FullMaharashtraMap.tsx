"use client";

import React from "react";
import Link from "next/link";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapProject } from "../../types";

const createStatusIcon = (status: string | null | undefined) => {
  const s = (status || "").toLowerCase();
  let color = "#2563EB"; // Blue (Active / Ongoing)
  if (s.includes("completed")) {
    color = "#16A34A"; // Green (Completed)
  } else if (s.includes("lapsed")) {
    color = "#D97706"; // Amber (Lapsed)
  } else if (s.includes("de-registered") || s.includes("revoked")) {
    color = "#DC2626"; // Red (De-registered)
  }

  const svgIcon = `
    <svg width="24" height="32" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0C5.373 0 0 5.373 0 12C0 21 12 32 12 32C12 32 24 21 24 12C24 5.373 18.627 0 12 0Z" fill="${color}" stroke="#FFFFFF" stroke-width="1.5"/>
      <circle cx="12" cy="12" r="4.5" fill="#FFFFFF"/>
    </svg>
  `;

  return L.divIcon({
    html: svgIcon,
    className: "custom-leaflet-marker",
    iconSize: [24, 32],
    iconAnchor: [12, 32],
    popupAnchor: [0, -32],
  });
};

interface FullMaharashtraMapProps {
  projects: MapProject[];
}

export default function FullMaharashtraMap({ projects }: FullMaharashtraMapProps) {
  // Center roughly around Maharashtra (19.0760 N, 73.8777 E)
  const defaultCenter: [number, number] = [18.98, 73.12];

  return (
    <MapContainer
      center={defaultCenter}
      zoom={10}
      scrollWheelZoom={true}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {projects.map((p) => (
        <Marker
          key={p.rera_id}
          position={[p.latitude, p.longitude]}
          icon={createStatusIcon(p.project_status)}
        >
          <Popup>
            <div className="p-1 text-xs space-y-1">
              <span className="font-mono text-[10px] font-bold text-blue-600 block">
                {p.rera_id}
              </span>
              <h4 className="font-bold text-gray-900 text-sm leading-snug">
                {p.project_name || "Unnamed"}
              </h4>
              <div className="flex items-center gap-1.5 text-gray-500 text-[11px]">
                <span>{p.district || "Maharashtra"}</span>
                <span>•</span>
                <span className="font-medium text-gray-800">{p.project_status || "Unknown"}</span>
              </div>
              <div className="pt-2">
                <Link
                  href={`/projects/${p.rera_id}`}
                  className="inline-block text-[11px] font-semibold text-white bg-blue-600 hover:bg-blue-700 px-2.5 py-1 rounded transition"
                >
                  View Complete Profile &rarr;
                </Link>
              </div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

