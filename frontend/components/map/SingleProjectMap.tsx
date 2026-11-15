"use client";

import React from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Leaflet icon fix for Next.js / Webpack
const customMarkerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface SingleProjectMapProps {
  latitude: number;
  longitude: number;
  projectName: string;
}

export default function SingleProjectMap({
  latitude,
  longitude,
  projectName,
}: SingleProjectMapProps) {
  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={14}
      scrollWheelZoom={false}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[latitude, longitude]} icon={customMarkerIcon}>
        <Popup>
          <div className="text-xs">
            <span className="font-bold text-gray-900">{projectName}</span>
            <div className="text-gray-500 mt-1">
              {latitude.toFixed(4)}, {longitude.toFixed(4)}
            </div>
          </div>
        </Popup>
      </Marker>
    </MapContainer>
  );
}

