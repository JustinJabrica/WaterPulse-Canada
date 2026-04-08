"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 overflow-x-hidden">
      <Navbar transparent />

      {/* Dark hero matching the landing page */}
      <header className="relative flex-1 flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0d2137] via-[#12304d] to-[#0f2a44]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
          }}
        />

        <div className="relative z-10 max-w-2xl mx-auto px-6 text-center">
          <h1 className="font-display text-7xl sm:text-8xl text-white/20 mb-4">
            404
          </h1>
          <h2 className="font-display text-3xl sm:text-4xl text-white mb-4">
            Page not found
          </h2>
          <p className="text-slate-300 text-lg mb-10 max-w-md mx-auto">
            The page you&rsquo;re looking for doesn&rsquo;t exist or has been moved.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-sm font-bold text-white bg-[#2196f3] hover:bg-[#42a5f5] transition-all duration-200 shadow-lg shadow-blue-900/30"
            >
              Go to Dashboard
            </Link>
            <Link
              href="/"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl text-sm font-semibold bg-white/10 text-white border border-white/15 hover:bg-white/15 backdrop-blur-sm transition-all duration-200"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </header>

      <Footer />
    </div>
  );
}
