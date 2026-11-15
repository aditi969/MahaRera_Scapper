import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalItems?: number;
  pageSize?: number;
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  totalItems,
  pageSize,
}) => {
  if (totalPages <= 1 && !totalItems) return null;

  const startItem = totalItems ? (currentPage - 1) * (pageSize || 20) + 1 : null;
  const endItem = totalItems ? Math.min(currentPage * (pageSize || 20), totalItems) : null;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-gray-200 sm:px-6">
      <div className="text-xs text-gray-500">
        {totalItems ? (
          <span>
            Showing <span className="font-semibold text-gray-700">{startItem}</span> to{" "}
            <span className="font-semibold text-gray-700">{endItem}</span> of{" "}
            <span className="font-semibold text-gray-700">{totalItems}</span> results
          </span>
        ) : (
          <span>
            Page <span className="font-semibold text-gray-700">{currentPage}</span> of{" "}
            <span className="font-semibold text-gray-700">{totalPages}</span>
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <ChevronLeft size={14} /> Previous
        </button>
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
};

