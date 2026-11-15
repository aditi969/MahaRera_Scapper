import React from "react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center bg-white rounded-2xl border border-gray-100 shadow-sm mx-auto max-w-xl my-12">
      <div className="text-4xl font-extrabold text-blue-600 mb-2">404</div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Page Not Found</h2>
      <p className="text-sm text-gray-600 mb-6">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
      >
        Return to Overview
      </Link>
    </div>
  );
}

