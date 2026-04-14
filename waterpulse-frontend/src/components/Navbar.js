"use client";

import { useState, useEffect, useRef } from "react";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!transparent) return;

    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [transparent]);

  // Close dropdowns when clicking outside
  const navRef = useRef(null);

  useEffect(() => {
    if (!menuOpen && !mobileOpen) return;
    const handleClick = (e) => {
      if (menuOpen && menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
      if (mobileOpen && navRef.current && !navRef.current.contains(e.target)) {
        setMobileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen, mobileOpen]);

  // Solid background when not transparent, or after scroll
  const isSolid = !transparent || scrolled;

  return (
    <nav
      ref={navRef}
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

        {/* Desktop nav */}
        <div className="hidden sm:flex items-center gap-3">
          <Link
            href="/dashboard"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              isSolid
                ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                : "text-white/80 hover:text-white hover:bg-white/10"
            }`}
          >
            Dashboard
          </Link>
          <Link
            href="/map"
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              isSolid
                ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                : "text-white/80 hover:text-white hover:bg-white/10"
            }`}
          >
            Map
          </Link>
          {isAuthenticated ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((prev) => !prev)}
                className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
                  isSolid
                    ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    : "text-white/80 hover:text-white hover:bg-white/10"
                }`}
              >
                {user?.username}
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-1 w-44 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
                  <Link
                    href="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    Profile
                  </Link>
                  <button
                    onClick={() => { setMenuOpen(false); logout(); }}
                    className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    Log Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors duration-200 shadow-sm bg-[#1e6ba8] hover:bg-[#185d94] shadow-blue-900/20"
            >
              Log In
            </Link>
          )}
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen((prev) => !prev)}
          className={`sm:hidden p-2 rounded-lg transition-colors cursor-pointer ${
            isSolid
              ? "text-slate-600 hover:bg-slate-100"
              : "text-white/80 hover:bg-white/10"
          }`}
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {mobileOpen ? (
              <><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>
            ) : (
              <><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></>
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu panel */}
      {mobileOpen && (
        <div className="sm:hidden bg-white border-t border-slate-200 shadow-lg">
          <div className="px-6 py-3 space-y-1">
            <Link
              href="/dashboard"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-2.5 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/map"
              onClick={() => setMobileOpen(false)}
              className="block px-4 py-2.5 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            >
              Map
            </Link>
            {isAuthenticated ? (
              <>
                <div className="border-t border-slate-100 my-1" />
                <Link
                  href="/profile"
                  onClick={() => setMobileOpen(false)}
                  className="block px-4 py-2.5 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Profile
                </Link>
                <button
                  onClick={() => { setMobileOpen(false); logout(); }}
                  className="w-full text-left px-4 py-2.5 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  Log Out
                </button>
              </>
            ) : (
              <>
                <div className="border-t border-slate-100 my-1" />
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="block px-4 py-2.5 rounded-lg text-sm font-semibold text-white text-center bg-[#1e6ba8] hover:bg-[#185d94] transition-colors"
                >
                  Log In
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
