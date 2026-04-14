"use client";

import { useState } from "react";
import useMapStore from "@/stores/mapStore";
import { PROVINCES } from "@/lib/constants";

const IconChevron = ({ className = "w-4 h-4", open }) => (
  <svg
    className={`${className} transition-transform ${open ? "rotate-180" : ""}`}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

const IconFilter = ({ className = "w-4 h-4" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
  </svg>
);

const TYPE_OPTIONS = [
  { value: "all", label: "All Types" },
  { value: "R", label: "River" },
  { value: "L", label: "Lake/Reservoir" },
];

const sortedProvinces = Object.entries(PROVINCES).sort(([, a], [, b]) =>
  a.localeCompare(b)
);

export default function MapFilterPanel() {
  const [expanded, setExpanded] = useState(false);

  const provinceFilter = useMapStore((s) => s.provinceFilter);
  const typeFilter = useMapStore((s) => s.typeFilter);
  const setProvinceFilter = useMapStore((s) => s.setProvinceFilter);
  const setTypeFilter = useMapStore((s) => s.setTypeFilter);
  const showNoData = useMapStore((s) => s.showNoData);
  const setShowNoData = useMapStore((s) => s.setShowNoData);
  const isLoading = useMapStore((s) => s.isLoading);
  const stations = useMapStore((s) => s.stations);

  const hasActiveFilters = provinceFilter !== null || typeFilter !== "all" || showNoData;

  return (
    <div>
      {/* Toggle button */}
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium shadow-md transition-colors cursor-pointer ${
          hasActiveFilters
            ? "bg-[#1e6ba8] text-white"
            : "bg-white text-slate-700 hover:bg-slate-50"
        }`}
      >
        <IconFilter />
        <span>Filters</span>
        {hasActiveFilters && (
          <span className="bg-white/20 text-xs px-1.5 py-0.5 rounded-full">
            {(provinceFilter ? 1 : 0) + (typeFilter !== "all" ? 1 : 0) + (showNoData ? 1 : 0)}
          </span>
        )}
        <IconChevron open={expanded} />
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="mt-2 w-64 bg-white rounded-lg shadow-lg border border-slate-200 p-4 space-y-4">
          {/* Province dropdown */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Province
            </label>
            <select
              value={provinceFilter || ""}
              onChange={(e) =>
                setProvinceFilter(e.target.value || null)
              }
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 transition-all"
            >
              <option value="">All Provinces</option>
              {sortedProvinces.map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {/* Station type toggle */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Station Type
            </label>
            <div className="flex gap-1">
              {TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setTypeFilter(opt.value)}
                  className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    typeFilter === opt.value
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Show inactive stations toggle */}
          <div className="flex items-center justify-between">
            <label
              htmlFor="showNoData"
              className="text-xs font-medium text-slate-500 cursor-pointer"
            >
              Show inactive stations
            </label>
            <button
              id="showNoData"
              role="switch"
              aria-checked={showNoData}
              onClick={() => setShowNoData(!showNoData)}
              className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer ${
                showNoData ? "bg-[#1e6ba8]" : "bg-slate-300"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                  showNoData ? "translate-x-4" : ""
                }`}
              />
            </button>
          </div>

          {/* Station count + clear */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <span className="text-xs text-slate-400">
              {isLoading ? "Loading..." : `${stations.length} stations`}
            </span>
            {hasActiveFilters && (
              <button
                onClick={() => {
                  setProvinceFilter(null);
                  setTypeFilter("all");
                  setShowNoData(false);
                }}
                className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors cursor-pointer"
              >
                Clear All
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
