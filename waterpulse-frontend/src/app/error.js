"use client";

import Link from "next/link";
import WaterPulseLogo from "@/components/WaterPulseLogo";

export default function GlobalError({ error, reset }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-6">
      <WaterPulseLogo variant="stacked" size="medium" />

      <h1 className="font-display text-2xl text-slate-900 mt-8 mb-2">
        Something went wrong
      </h1>
      <p className="text-sm text-slate-500 text-center max-w-md mb-8">
        {error?.message || "An unexpected error occurred. Please try again."}
      </p>

      <div className="flex items-center gap-3">
        <button
          onClick={reset}
          className="px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-[#2196f3] hover:bg-[#42a5f5] transition-colors shadow-sm"
        >
          Try Again
        </button>
        <Link
          href="/dashboard"
          className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:border-[#2196f3]/40 hover:text-[#1e6ba8] transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
