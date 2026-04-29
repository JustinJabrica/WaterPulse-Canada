"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import useMapStore from "@/stores/mapStore";
import RatingPill from "@/components/RatingPill";
import api from "@/lib/api";
import { useAuth } from "@/context/authcontext";
import {
  computeReadingSummary,
  computeWeatherSummary,
  formatTime,
  midpoint,
} from "@/lib/aggregateStations";
import useStationWeatherBatch from "@/lib/useStationWeatherBatch";

/* ── Inline icons ────────────────────────────── */

const IconX = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const IconPlus = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

const IconLoader = ({ className = "w-4 h-4" }) => (
  <svg className={`${className} animate-spin`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" className="opacity-25" /><path d="M4 12a8 8 0 018-8" className="opacity-75" />
  </svg>
);

/* ── Summary stat row ────────────────────────── */

function SummaryStat({ label, value, unit, high, low, rating }) {
  return (
    <div className="py-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-900">{label}</span>
        <div className="flex items-center gap-2">
          {rating && <RatingPill rating={rating} />}
          <span className="text-sm font-semibold text-slate-900">
            {value != null ? `${value} ${unit}` : "—"}
          </span>
        </div>
      </div>
      {(high || low) && (
        <div className="flex gap-3 mt-0.5">
          {high && (
            <span className="text-xs text-blue-600" title={high.name}>
              High: {high.value} {unit} ({high.name})
            </span>
          )}
          {low && (
            <span className="text-xs text-amber-600" title={low.name}>
              Low: {low.value} {unit} ({low.name})
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main component ──────────────────────────── */

export default function SelectionSummaryPanel() {
  const selectedStations = useMapStore((s) => s.selectedStations);
  const toggleStationSelection = useMapStore((s) => s.toggleStationSelection);
  const clearSelection = useMapStore((s) => s.clearSelection);
  const setViewState = useMapStore((s) => s.setViewState);
  const viewState = useMapStore((s) => s.viewState);
  const { isAuthenticated } = useAuth();

  const { weatherCache, loading: weatherLoading } =
    useStationWeatherBatch(selectedStations);

  const [nearbyStations, setNearbyStations] = useState([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);

  const selectedNumbers = useMemo(
    () => new Set(selectedStations.map((s) => s.station_number)),
    [selectedStations]
  );

  // ── Fetch nearby stations ────────────────────
  useEffect(() => {
    if (selectedStations.length === 0) {
      setNearbyStations([]);
      return;
    }

    let cancelled = false;
    setNearbyLoading(true);

    const center = midpoint(selectedStations);
    api
      .get("/api/stations/nearby", {
        params: { lat: center.lat, lon: center.lon, radius: 50, limit: 15 },
      })
      .then((data) => {
        if (!cancelled) setNearbyStations(data);
      })
      .catch(() => {
        if (!cancelled) setNearbyStations([]);
      })
      .finally(() => {
        if (!cancelled) setNearbyLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedStations]);

  const readingSummary = useMemo(
    () => computeReadingSummary(selectedStations),
    [selectedStations]
  );

  const weatherSummary = useMemo(
    () => computeWeatherSummary(selectedStations, weatherCache),
    [selectedStations, weatherCache]
  );

  // Nearby stations not already selected
  const filteredNearby = useMemo(
    () => nearbyStations.filter((s) => !selectedNumbers.has(s.station_number)),
    [nearbyStations, selectedNumbers]
  );

  if (selectedStations.length === 0) return null;

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10 h-1/3 overflow-y-auto bg-white rounded-t-lg shadow-lg border border-slate-200 md:bottom-auto md:left-auto md:top-3 md:right-3 md:h-auto md:w-80 md:max-h-[calc(100%-24px)] md:rounded-lg">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-slate-100 px-4 py-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">
          Selection ({selectedStations.length})
        </h2>
        <div className="flex items-center gap-2">
          {isAuthenticated && (
            <Link
              href={`/collections/new?stations=${selectedStations
                .map((s) => s.station_number)
                .join(",")}`}
              className="text-xs px-2 py-1 rounded-md bg-[#2196f3] text-white font-medium hover:bg-[#1e6ba8] transition-colors"
              title="Save these stations as a new collection"
            >
              Save as Collection
            </Link>
          )}
          <button
            onClick={clearSelection}
            className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors cursor-pointer"
          >
            Clear All
          </button>
        </div>
      </div>

      <div className="px-4 py-3 space-y-4">
        {/* Selected station chips */}
        <div className="flex flex-col gap-1.5">
          {selectedStations.map((station) => (
            <span
              key={station.station_number}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs text-blue-800"
            >
              <button
                onClick={() =>
                  setViewState({
                    ...viewState,
                    latitude: station.latitude,
                    longitude: station.longitude,
                    zoom: 12,
                  })
                }
                className="truncate flex-1 min-w-0 text-center hover:text-[#1e6ba8] hover:underline transition-colors cursor-pointer"
                title={station.station_name}
              >
                {station.station_name}
              </button>
              <button
                onClick={() => toggleStationSelection(station)}
                className="hover:text-red-600 transition-colors cursor-pointer"
              >
                <IconX className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>

        {/* Aggregated readings */}
        <div className="border-t border-slate-100 pt-2">
          <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1">
            Readings
          </h3>
          <SummaryStat
            label="Avg Flow"
            value={readingSummary.avgFlow}
            unit="m³/s"
            high={readingSummary.highFlow}
            low={readingSummary.lowFlow}
            rating={readingSummary.dominantFlowRating}
          />
          <SummaryStat
            label="Avg Level"
            value={readingSummary.avgLevel}
            unit="m"
            high={readingSummary.highLevel}
            low={readingSummary.lowLevel}
            rating={readingSummary.dominantLevelRating}
          />
        </div>

        {/* Aggregated weather */}
        <div className="border-t border-slate-100 pt-2">
          <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1">
            Weather
            {weatherLoading && (
              <IconLoader className="inline ml-2 w-3 h-3 text-slate-400" />
            )}
          </h3>
          {weatherSummary.loadedCount > 0 ? (
            <>
              <SummaryStat
                label="Avg Temperature"
                value={weatherSummary.avgTemp}
                unit="°C"
                high={weatherSummary.highTemp}
                low={weatherSummary.lowTemp}
              />
              <div className="flex items-center justify-between py-2">
                <span className="text-xs text-slate-900">Sunrise (earliest)</span>
                <span className="text-sm font-semibold text-slate-900">
                  {weatherSummary.earliestSunrise
                    ? formatTime(weatherSummary.earliestSunrise.value)
                    : "—"}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-xs text-slate-900">Sunset (latest)</span>
                <span className="text-sm font-semibold text-slate-900">
                  {weatherSummary.latestSunset
                    ? formatTime(weatherSummary.latestSunset.value)
                    : "—"}
                </span>
              </div>
            </>
          ) : weatherLoading ? (
            <p className="text-xs text-slate-400 py-2">Loading weather data...</p>
          ) : (
            <p className="text-xs text-slate-400 py-2">No weather data available</p>
          )}
        </div>

        {/* Nearby stations */}
        {filteredNearby.length > 0 && (
          <div className="border-t border-slate-100 pt-2">
            <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2">
              Nearby Stations
              {nearbyLoading && (
                <IconLoader className="inline ml-2 w-3 h-3 text-slate-400" />
              )}
            </h3>
            <div className="space-y-1">
              {filteredNearby.slice(0, 8).map((station) => (
                <div
                  key={station.station_number}
                  className="flex items-center justify-between py-1.5"
                >
                  <div className="min-w-0 flex-1 mr-2">
                    <p className="text-xs font-medium text-slate-900 truncate">
                      {station.station_name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {station.station_number}
                    </p>
                  </div>
                  <button
                    onClick={() => toggleStationSelection(station)}
                    className="flex items-center gap-0.5 px-2 py-1 rounded-md text-xs font-medium text-[#1e6ba8] bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors cursor-pointer"
                  >
                    <IconPlus className="w-3 h-3" />
                    Add
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
