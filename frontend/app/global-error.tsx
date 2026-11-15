"use client";

import React from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="flex items-center justify-center min-h-screen bg-gray-50 p-6">
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100 max-w-md w-full text-center">
          <div className="text-3xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Application Error</h2>
          <p className="text-sm text-gray-600 mb-6">
            {error.message || "A critical application error occurred."}
          </p>
          <button
            onClick={() => reset()}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors text-sm"
          >
            Recover
          </button>
        </div>
      </body>
    </html>
  );
}

