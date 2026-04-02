"use client";

import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import StationDetail from "@/components/StationDetail";

/**
 * Full-page station view — used when visiting /station/[number] directly
 * (e.g., shared link, page refresh, or browser that doesn't support the
 * intercepting-route modal).
 */
export default function StationDetailPage() {
  const { station_number } = useParams();
  const router = useRouter();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />

      <main className="flex-1 pt-20 pb-12 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          {/* Back button */}
          <div className="mb-6">
            <button
              onClick={() => router.back()}
              className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-[#1e6ba8] transition-colors"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
              </svg>
              Dashboard
            </button>
          </div>

          <StationDetail stationNumber={station_number} />
        </div>
      </main>

      <Footer />
    </div>
  );
}
