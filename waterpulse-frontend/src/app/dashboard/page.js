"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import StationCard from "@/components/StationCard";
import FeaturedCollections from "./FeaturedCollections";
import useDashboardStore from "@/stores/dashboardStore";
import api from "@/lib/api";
import { PROVINCES, STATION_TYPES } from "@/lib/constants";

/* ─────────────────────────────────────────────
   Dashboard — Browse stations by province
   ───────────────────────────────────────────── */

// Number of station cards to render per "page". The dashboard uses infinite
// scroll — only PAGE_SIZE cards are shown initially. When the user scrolls
// near the bottom, PAGE_SIZE more are appended automatically via an
// IntersectionObserver watching a sentinel element below the grid.
const PAGE_SIZE = 15;

// ── Inline icons ────────────────────────────

const IconSearch = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconRefresh = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
  </svg>
);

const IconLoader = ({ className = "w-4 h-4" }) => (
  <svg className={`${className} animate-spin`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" className="opacity-25" />
    <path d="M4 12a8 8 0 018-8" className="opacity-75" />
  </svg>
);

/** Derive the most recent fetched_at from loaded station readings. */
function getLatestFetchedAt(stations) {
  let latest = null;
  for (const s of stations) {
    const ts = s.latest_reading?.fetched_at;
    if (!ts) continue;
    const d = new Date(ts.endsWith("Z") ? ts : ts + "Z");
    if (!latest || d > latest) latest = d;
  }
  return latest;
}


export default function DashboardPage() {
  // ── Persistent state (survives navigation via Zustand) ──
  const selectedProvince = useDashboardStore((s) => s.selectedProvince);
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const typeFilter = useDashboardStore((s) => s.typeFilter);
  const setSelectedProvince = useDashboardStore((s) => s.setSelectedProvince);
  const setSearchQuery = useDashboardStore((s) => s.setSearchQuery);
  const setTypeFilter = useDashboardStore((s) => s.setTypeFilter);
  const showNoData = useDashboardStore((s) => s.showNoData);
  const setShowNoData = useDashboardStore((s) => s.setShowNoData);
  const clearSearch = useDashboardStore((s) => s.clearSearch);

  // ── Local state (resets each visit, which is fine) ──
  const [provinces, setProvinces] = useState([]);
  const [stations, setStations] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [provinceError, setProvinceError] = useState(null);
  const [stationError, setStationError] = useState(null);
  const [refreshError, setRefreshError] = useState(null);

  // ── Infinite scroll state ──
  // displayCount tracks how many cards from filteredStations to render.
  // Starts at PAGE_SIZE (15) and grows by PAGE_SIZE each time the user
  // scrolls near the bottom. Reset back to PAGE_SIZE whenever the province,
  // filters, or search results change.
  const [displayCount, setDisplayCount] = useState(PAGE_SIZE);

  // Ref for the sentinel element placed below the station grid. An
  // IntersectionObserver watches this element — when it enters the
  // viewport (or comes within 200px), we load the next batch of cards.
  const sentinelRef = useRef(null);

  // Track whether this is the first province load (to avoid clearing a restored search)
  const isFirstLoad = useRef(true);

  // ── Load provinces (called on mount + retry) ──
  const loadProvinces = useCallback(async () => {
    try {
      setProvinceError(null);
      const data = await api.get("/api/stations/provinces");
      data.sort((a, b) => a.province_code.localeCompare(b.province_code));
      setProvinces(data);
      if (!selectedProvince && data.length > 0) {
        setSelectedProvince(data[0].province_code);
      }
    } catch (error) {
      console.error("Failed to load provinces:", error);
      setProvinceError("Could not load provinces. The server may be unavailable.");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { loadProvinces(); }, [loadProvinces]);

  // ── Load stations when province changes ───
  const loadStations = useCallback(async () => {
    if (!selectedProvince) return;
    setLoading(true);
    setStationError(null);
    // Don't clear search on the first load — it was restored from the store
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
    } else {
      setSearchResults(null);
      clearSearch();
    }
    try {
      const data = await api.get(
        `/api/readings/by-province/${selectedProvince}`
      );
      setStations(data);
      setLastUpdated(getLatestFetchedAt(data));
    } catch (error) {
      console.error("Failed to load stations:", error);
      setStations([]);
      setStationError("Could not load station data. Please try again.");
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProvince]);

  useEffect(() => { loadStations(); }, [loadStations]);

  // Auto-refresh removed — the backend scheduler keeps data fresh.
  // Users can still manually refresh via the refresh button.

  // ── Infinite scroll: reset displayCount when inputs change ──
  // Whenever the user switches province, changes a filter, or gets new
  // search results, we reset back to showing the first PAGE_SIZE cards.
  useEffect(() => {
    setDisplayCount(PAGE_SIZE);
  }, [selectedProvince, typeFilter, showNoData, searchResults]);

  // ── Infinite scroll: observe sentinel to load more cards ──
  // An IntersectionObserver watches the sentinel div below the grid.
  // rootMargin "200px" triggers 200px before the sentinel is visible,
  // so new cards appear seamlessly before the user hits the bottom.
  // Dependencies use the raw inputs (stations, searchResults, typeFilter,
  // showNoData) rather than the derived filteredStations array, because
  // filteredStations is computed further down in the component body.
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setDisplayCount((prev) => prev + PAGE_SIZE);
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [stations, searchResults, typeFilter, showNoData]);

  // ── Refresh readings for current province ─
  const handleRefresh = useCallback(async () => {
    if (!selectedProvince || refreshing) return;
    setRefreshing(true);
    setRefreshError(null);
    try {
      await api.post(
        `/api/readings/refresh?province=${selectedProvince}`
      );
      // Re-fetch station data after refresh
      const data = await api.get(
        `/api/readings/by-province/${selectedProvince}`
      );
      setStations(data);
      setLastUpdated(getLatestFetchedAt(data));
    } catch (error) {
      console.error("Refresh failed:", error);
      setRefreshError("Refresh failed. Please try again.");
    } finally {
      setRefreshing(false);
    }
  }, [selectedProvince, refreshing]);

  // ── Search ────────────────────────────────
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(null);
      return;
    }

    const timeout = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const data = await api.get(
          `/api/stations/search?q=${encodeURIComponent(searchQuery)}&province=${selectedProvince}&limit=200`
        );
        setSearchResults(data);
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => clearTimeout(timeout);
  }, [searchQuery, selectedProvince]);

  // ── Filter stations (memoized) ─────────────
  // All derived station lists and counts are wrapped in useMemo so they
  // only recalculate when their dependencies actually change, rather
  // than on every render (typing, scrolling, any state change).

  const displayStations = useMemo(
    () => searchResults || stations,
    [searchResults, stations]
  );

  const filteredStations = useMemo(() => {
    const withDataFilter = showNoData
      ? displayStations
      : displayStations.filter((s) => s.latest_reading != null);
    return typeFilter === "all"
      ? withDataFilter
      : withDataFilter.filter((s) => s.station_type === typeFilter);
  }, [displayStations, showNoData, typeFilter]);

  // Station counts derived from displayStations — only recalculated
  // when the base station list changes (province switch or search).
  const { activeRiverCount, activeLakeCount, hiddenCount } = useMemo(() => {
    const active = displayStations.filter((s) => s.latest_reading != null);
    return {
      activeRiverCount: active.filter((s) => s.station_type === "R").length,
      activeLakeCount: active.filter((s) => s.station_type === "L").length,
      hiddenCount: displayStations.length - active.length,
    };
  }, [displayStations]);

  // Counts used by the "Showing X active of Y total" counter —
  // depends on the current filters applied to the station list.
  const { totalForType, activeFilteredCount } = useMemo(() => ({
    totalForType: typeFilter === "all"
      ? displayStations.length
      : displayStations.filter((s) => s.station_type === typeFilter).length,
    activeFilteredCount: filteredStations.filter((s) => s.latest_reading != null).length,
  }), [displayStations, filteredStations, typeFilter]);

  // Type badge counts — only recalculated when base station list changes.
  const typeCounts = useMemo(() => {
    const counts = {};
    displayStations.forEach((s) => {
      const t = s.station_type || "?";
      counts[t] = (counts[t] || 0) + 1;
    });
    return counts;
  }, [displayStations]);

  const provinceName = PROVINCES[selectedProvince] || selectedProvince;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col overflow-x-hidden">
      <Navbar />

      <main className="flex-1 pt-20 pb-12 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto">

          {/* ── Header ────────────────────────── */}
          <div className="mb-8">
            <h1 className="font-display text-3xl sm:text-4xl text-slate-900 mb-2">
              Dashboard
            </h1>
            <p className="text-slate-900">
              Browse water conditions across Canada. Select a province to view
              station readings.
            </p>
          </div>

          {/* ── Province error ────────────────── */}
          {provinceError && (
            <div className="mb-6 px-4 py-3 rounded-lg bg-red-50 border border-red-200 flex items-center justify-between">
              <span className="text-red-700 text-sm">{provinceError}</span>
              <button
                onClick={loadProvinces}
                className="ml-4 px-3 py-1 rounded-md text-xs font-medium text-red-700 bg-red-100 hover:bg-red-200 transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* ── Province picker ────────────────── */}
          <div className="mb-6">
            <div className="flex flex-wrap gap-2">
              {provinces.map((prov) => {
                const isActive = prov.province_code === selectedProvince;
                return (
                  <button
                    key={prov.province_code}
                    onClick={() => setSelectedProvince(prov.province_code)}
                    className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                      isActive
                        ? "bg-[#1e6ba8] text-white shadow-sm"
                        : "bg-white text-slate-900 border border-slate-200 hover:border-[#2196f3]/40 hover:text-[#1e6ba8]"
                    }`}
                  >
                    {prov.province_code}
                    <span className={`ml-1.5 text-xs ${isActive ? "text-blue-200" : "text-slate-900"}`}>
                      {prov.total_stations}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Search + controls row ─────────── */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
            {/* Search bar */}
            <div className="relative flex-1 w-full sm:max-w-sm">
              <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search stations by name..."
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 text-sm bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 transition-all"
              />
              {searchLoading && (
                <IconLoader className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              )}
            </div>

            {/* Type filter */}
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setTypeFilter("all")}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  typeFilter === "all"
                    ? "bg-slate-900 text-white"
                    : "bg-white text-slate-900 border border-slate-200 hover:text-[#1e6ba8]"
                }`}
              >
                All
              </button>
              {Object.entries(STATION_TYPES).map(([code, label]) => (
                <button
                  key={code}
                  onClick={() => setTypeFilter(code)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    typeFilter === code
                      ? "bg-slate-900 text-white"
                      : "bg-white text-slate-900 border border-slate-200 hover:text-[#1e6ba8]"
                  }`}
                >
                  {label}
                  {typeCounts[code] != null && (
                    <span className="ml-1 text-[10px] opacity-60">
                      {typeCounts[code]}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Show stations without data toggle */}
            <button
              onClick={() => setShowNoData(!showNoData)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all ${
                showNoData
                  ? "bg-slate-900 text-white"
                  : "bg-white border border-slate-200 text-slate-900 hover:text-[#1e6ba8] hover:border-[#2196f3]/40"
              }`}
            >
              Show Inactive Stations
              {hiddenCount > 0 && (
                <span className={`text-[10px] ${showNoData ? "opacity-60" : "opacity-50"}`}>
                  {hiddenCount}
                </span>
              )}
            </button>

            {/* Refresh button — pushed to the right so it aligns above "Last updated" */}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="ml-auto inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-900 hover:text-[#1e6ba8] hover:border-[#2196f3]/40 disabled:opacity-50 transition-all"
            >
              {refreshing ? (
                <IconLoader className="w-3.5 h-3.5" />
              ) : (
                <IconRefresh className="w-3.5 h-3.5" />
              )}
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {/* ── Refresh error ────────────────── */}
          {refreshError && (
            <div className="mb-4 px-4 py-2.5 rounded-lg bg-red-50 border border-red-200">
              <span className="text-red-700 text-sm">{refreshError}</span>
            </div>
          )}

          {/* ── Province header + freshness ────── */}
          {selectedProvince && !searchResults && (
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-xl text-slate-900">
                {provinceName}
                <span className="text-sm font-normal text-slate-900 ml-2">
                  {activeRiverCount} River and {activeLakeCount} Lake/Reservoir Station{activeRiverCount + activeLakeCount !== 1 ? "s" : ""} Active
                </span>
              </h2>
              {lastUpdated && (
                <span className="text-xs text-slate-900">
                  Last updated {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>
          )}

          {/* ── Search header ─────────────────── */}
          {searchResults && (
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm text-slate-900">
                {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}{" "}
                for &ldquo;{searchQuery}&rdquo;
              </h2>
              <button
                onClick={() => { clearSearch(); setSearchResults(null); }}
                className="text-xs text-[#2196f3] hover:underline"
              >
                Clear search
              </button>
            </div>
          )}

          {/* ── Featured Collections strip ────── */}
          <FeaturedCollections />

          {/* ── Station grid ──────────────────── */}
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <IconLoader className="w-6 h-6 text-[#2196f3]" />
              <span className="ml-2 text-sm text-slate-900">Loading stations...</span>
            </div>
          ) : stationError ? (
            <div className="flex flex-col items-center justify-center py-24">
              <p className="text-red-700 text-sm mb-4">{stationError}</p>
              <button
                onClick={loadStations}
                className="px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-[#2196f3] hover:bg-[#42a5f5] transition-colors shadow-sm"
              >
                Retry
              </button>
            </div>
          ) : filteredStations.length === 0 ? (
            <div className="text-center py-24">
              <p className="text-slate-900 text-sm">
                {searchQuery
                  ? "No stations match your search."
                  : "No stations found for this filter."}
              </p>
            </div>
          ) : (
            <>
              {/* ── Station count summary ──
                   When showNoData is on (inactive stations visible), shows
                   "Showing all Y stations." When off, shows how many active
                   stations exist out of the total for the current filters. */}
              <p className="text-xs text-slate-900 mb-3">
                {showNoData
                  ? `Showing all ${filteredStations.length} station${filteredStations.length !== 1 ? "s" : ""}.`
                  : `Showing ${activeFilteredCount} active station${activeFilteredCount !== 1 ? "s" : ""} of ${totalForType} total.`}
              </p>

              {/* ── Station card grid ──
                   Only render the first `displayCount` cards (controlled by
                   infinite scroll). slice(0, displayCount) is safe when
                   displayCount exceeds the array length — it just returns all. */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredStations.slice(0, displayCount).map((station) => (
                  <StationCard
                    key={station.station_number}
                    station={station}
                  />
                ))}
              </div>

              {/* ── Infinite scroll sentinel ──
                   This invisible div sits below the grid. An IntersectionObserver
                   (set up in the useEffect above) watches it — when the user
                   scrolls within 200px of it, displayCount increments by PAGE_SIZE
                   and the next batch of cards renders. Hidden once all cards are
                   visible so the observer stops firing. */}
              {displayCount < filteredStations.length && (
                <div
                  ref={sentinelRef}
                  className="flex items-center justify-center py-8"
                >
                  <IconLoader className="w-5 h-5 text-[#2196f3]" />
                  <span className="ml-2 text-sm text-slate-500">
                    Loading more stations...
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
