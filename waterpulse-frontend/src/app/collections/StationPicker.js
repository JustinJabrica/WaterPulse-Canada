"use client";

import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";

const DEBOUNCE_MS = 600;
const MIN_QUERY = 2;
const MAX_RESULTS = 10;

const IconSearch = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconPlus = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconCheck = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

/**
 * Search-as-you-type station picker. Calls onAdd(stationNumber) when the
 * user clicks Add on a result. Already-attached stations show a check
 * instead of an Add button.
 *
 * Props:
 *   alreadyAdded   — Set of station_numbers already in the collection
 *   onAdd          — async (stationNumber) => unknown
 */
export default function StationPicker({ alreadyAdded, onAdd }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [pending, setPending] = useState(new Set());
  const abortRef = useRef(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY) {
      setResults([]);
      setStatus("idle");
      if (abortRef.current) abortRef.current.abort();
      return;
    }

    const handle = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStatus("loading");
      try {
        const data = await api.get("/api/stations/search", {
          params: { q: trimmed, limit: MAX_RESULTS },
          signal: controller.signal,
        });
        setResults(Array.isArray(data) ? data : []);
        setStatus("idle");
      } catch (err) {
        if (err?.code === "ERR_CANCELED" || controller.signal.aborted) return;
        setResults([]);
        setStatus("error");
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(handle);
  }, [query]);

  const handleAdd = async (stationNumber) => {
    if (pending.has(stationNumber)) return;
    setPending((prev) => new Set(prev).add(stationNumber));
    try {
      await onAdd(stationNumber);
    } finally {
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(stationNumber);
        return next;
      });
    }
  };

  return (
    <div>
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <IconSearch />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search stations by name or number"
          className="w-full pl-8 pr-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 text-sm"
        />
      </div>

      {status === "loading" && (
        <p className="text-xs text-slate-500 mt-2">Searching…</p>
      )}
      {status === "error" && (
        <p className="text-xs text-red-500 mt-2">Search failed</p>
      )}

      {results.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
          {results.map((station) => {
            const added = alreadyAdded.has(station.station_number);
            const busy = pending.has(station.station_number);
            return (
              <li
                key={station.station_number}
                className="flex items-center gap-3 px-3 py-2 bg-white"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {station.station_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {station.station_number}
                    {station.province ? ` • ${station.province}` : ""}
                    {station.station_type ? ` • ${station.station_type}` : ""}
                  </p>
                </div>
                {added ? (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-medium">
                    <IconCheck className="w-3.5 h-3.5" />
                    Added
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleAdd(station.station_number)}
                    disabled={busy}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-[#2196f3] text-white text-xs font-medium hover:bg-[#1e6ba8] transition-colors cursor-pointer disabled:opacity-60"
                  >
                    <IconPlus className="w-3.5 h-3.5" />
                    {busy ? "Adding…" : "Add"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {query.trim().length >= MIN_QUERY &&
        status === "idle" &&
        results.length === 0 && (
          <p className="text-xs text-slate-500 mt-2">No matches</p>
        )}
    </div>
  );
}
