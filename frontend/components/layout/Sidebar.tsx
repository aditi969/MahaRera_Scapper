"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  BarChart3,
  MapPin,
  Terminal,
  ShieldCheck,
  Activity,
  Layers,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Project Explorer", href: "/projects", icon: Building2 },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Interactive Map", href: "/map", icon: MapPin },
  { label: "Scraper Control", href: "/scraper", icon: Terminal },
  { label: "Data Quality", href: "/data-quality", icon: ShieldCheck },
  { label: "System Status", href: "/system", icon: Activity },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-gray-100 gap-3">
        <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm">
          <Layers size={20} />
        </div>
        <div>
          <h1 className="text-sm font-bold text-gray-900 tracking-tight leading-none">
            RERA INSIGHT
          </h1>
          <p className="text-[10px] text-gray-400 font-medium tracking-wide mt-0.5 uppercase">
            Maharashtra Intelligence
          </p>
        </div>
      </div>

      {/* Navigation items */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">
          Platform
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition ${
                isActive
                  ? "bg-blue-50 text-blue-700 font-semibold"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <Icon
                size={18}
                className={isActive ? "text-blue-600" : "text-gray-400"}
              />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer / Scope info */}
      <div className="p-4 border-t border-gray-100">
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-gray-700">MahaRERA Live</span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1 leading-tight">
            Jurisdiction: Maharashtra RERA Active & Archived Registrations
          </p>
        </div>
      </div>
    </aside>
  );
};

