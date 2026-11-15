import React from "react";

export const Skeleton: React.FC<{ className?: string }> = ({ className = "" }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="w-full space-y-3 p-4">
    <div className="flex gap-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-6 w-48" />
      <Skeleton className="h-6 w-24" />
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex gap-4 items-center py-2 border-b border-gray-100">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-32" />
      </div>
    ))}
  </div>
);

export const CardSkeleton: React.FC = () => (
  <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
    <Skeleton className="h-4 w-24" />
    <Skeleton className="h-8 w-16" />
    <Skeleton className="h-3 w-36" />
  </div>
);

