import React from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: {
    text: string;
    variant: "primary" | "success" | "warning" | "danger" | "neutral";
  };
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badge,
}) => {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm transition hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-gray-900">{value}</span>
        {badge && (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              badge.variant === "success"
                ? "bg-green-100 text-green-700"
                : badge.variant === "warning"
                ? "bg-amber-100 text-amber-700"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            {badge.text}
          </span>
        )}
      </div>
      {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
    </div>
  );
};

