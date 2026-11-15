import "./globals.css";
import React from "react";
import { Sidebar } from "../components/layout/Sidebar";

export const metadata = {
  title: "RERA INSIGHT - Maharashtra Real Estate Data Intelligence Platform",
  description: "Enterprise data platform for exploring, validating, and monitoring MahaRERA registered projects.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-[#F7F8FA]">
        <Sidebar />
        <main className="flex-1 min-w-0 p-8 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}

