"use client";

import { useState } from "react";
import { RATING_CONFIG } from "@/lib/constants";
import useMapStore from "@/stores/mapStore";

const RATING_COLOURS = {
  "very low": "#ef4444",
  low: "#f59e0b",
  average: "#10b981",
  high: "#3b82f6",
  "very high": "#a855f7",
};

const LEGEND_ITEMS = Object.entries(RATING_CONFIG).map(([key, config]) => ({
  key,
  label: config.label,
  colour: RATING_COLOURS[key],
}));

export default function MapLegend() {
  const [expanded, setExpanded] = useState(true);
  const hasSelection = useMapStore((s) => s.selectedStations.length > 0);

  return (
    <div className={`absolute left-3 z-10 transition-all duration-200 ${
      hasSelection ? "bottom-[calc(33.33%+0.75rem)] md:bottom-6" : "bottom-6"
    }`}>
      {expanded ? (
        <div className="bg-white rounded-lg shadow-md border border-slate-200 px-3 py-2.5">
          <button
            onClick={() => setExpanded(false)}
            className="flex items-center justify-between w-full mb-1.5 cursor-pointer"
          >
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Rating
            </span>
            <svg className="w-3.5 h-3.5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 15 12 9 18 15" />
            </svg>
          </button>
          <div className="space-y-1">
            {LEGEND_ITEMS.map((item) => (
              <div key={item.key} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.colour }}
                />
                <span className="text-xs text-slate-700">{item.label}</span>
              </div>
            ))}
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: "#94a3b8" }}
              />
              <span className="text-xs text-slate-700">No Data</span>
            </div>
          </div>
          <button
            onClick={() => setExpanded(false)}
            className="w-full mt-2 pt-1.5 border-t border-slate-100 text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors cursor-pointer text-center"
          >
            Legend
          </button>
        </div>
      ) : (
        <button
          onClick={() => setExpanded(true)}
          className="bg-white rounded-lg shadow-md border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
        >
          Legend
        </button>
      )}
    </div>
  );
}
