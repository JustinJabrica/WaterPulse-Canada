"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import WaterPulseLogo from "@/components/WaterPulseLogo";
import { useAuth } from "@/context/authcontext";

/**
 * Navbar — shared site-wide navigation.
 *
 * Props:
 *   transparent  – when true the navbar starts see-through over a dark
 *                  hero section and turns solid on scroll (landing page).
 *                  When false (default) it is always solid (inner pages).
 */
export default function Navbar({ transparent = false }) {
  const [scrolled, setScrolled] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();

  useEffect(() => {
    if (!transparent) return;

    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [transparent]);

  // Solid background when not transparent, or after scroll
  const isSolid = !transparent || scrolled;

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isSolid
          ? "bg-white/90 backdrop-blur-md shadow-sm border-b border-slate-200/60"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo — light variant when over dark hero */}
        <Link href="/" className={isSolid ? "" : "logo-on-dark"}>
          <WaterPulseLogo variant="horizontal" size="small" />
        </Link>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <Link
                href="/dashboard"
                className={`hidden sm:inline-flex px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isSolid
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    : "text-white/80 hover:text-white hover:bg-white/10"
                }`}
              >
                Dashboard
              </Link>
              <button
                onClick={logout}
                className={`hidden sm:inline-flex px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isSolid
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    : "text-white/80 hover:text-white hover:bg-white/10"
                }`}
              >
                Log Out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className={`hidden sm:inline-flex px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isSolid
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    : "text-white/80 hover:text-white hover:bg-white/10"
                }`}
              >
                Log In
              </Link>
              <Link
                href="/register"
                className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors duration-200 shadow-sm bg-[#1e6ba8] hover:bg-[#185d94] shadow-blue-900/20"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
