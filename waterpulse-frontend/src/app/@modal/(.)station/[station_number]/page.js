"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useCallback } from "react";
import StationDetail from "@/components/StationDetail";

/**
 * Modal station view — rendered as an overlay when navigating from within
 * the app (e.g., clicking a StationCard on the dashboard). The page behind
 * stays fully rendered.
 *
 * If the user visits /station/[number] directly (shared link, refresh),
 * Next.js skips this intercepting route and shows the full page instead.
 */
export default function StationModalPage() {
  const { station_number } = useParams();
  const router = useRouter();

  const handleClose = useCallback(() => {
    router.back();
  }, [router]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleClose]);

  // Prevent body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal panel */}
      <div className="relative w-full max-w-4xl max-h-[90vh] mt-[5vh] mx-4 bg-slate-50 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-modal-enter">
        {/* Sticky header with close button */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-3 bg-white/80 backdrop-blur-sm border-b border-slate-200/60">
          <button
            onClick={handleClose}
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-[#1e6ba8] transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
            </svg>
            Back
          </button>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <StationDetail stationNumber={station_number} />
        </div>
      </div>
    </div>
  );
}
