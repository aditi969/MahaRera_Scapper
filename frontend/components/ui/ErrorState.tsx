import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message,
  onRetry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-red-50 rounded-xl border border-red-200">
      <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-3">
        <AlertCircle size={22} />
      </div>
      <h3 className="text-sm font-semibold text-red-900">{title}</h3>
      <p className="mt-1 text-xs text-red-600 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-white border border-red-300 rounded-lg hover:bg-red-50 transition"
        >
          <RotateCcw size={14} /> Retry
        </button>
      )}
    </div>
  );
};

