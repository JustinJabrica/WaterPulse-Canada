"use client";

import { useState, useEffect, useMemo } from "react";
import useMapStore from "@/stores/mapStore";
import RatingPill from "@/components/RatingPill";
import api from "@/lib/api";

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

/* ── Helpers ─────────────────────────────────── */

/** Find the mode (most frequent value) in an array of strings. */
function mode(values) {
  const counts = {};
  values.forEach((v) => {
    if (v) counts[v] = (counts[v] || 0) + 1;
  });
  let best = null;
  let bestCount = 0;
  for (const [val, count] of Object.entries(counts)) {
    if (count > bestCount) {
      best = val;
      bestCount = count;
    }
  }
  return best;
}

/** Format a time string (HH:MM or ISO) to a short local display. */
function formatTime(timeStr) {
  if (!timeStr) return null;
  try {
    const date = new Date(timeStr);
    if (isNaN(date.getTime())) return timeStr;
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return timeStr;
  }
}

/** Geographic midpoint of an array of {latitude, longitude} objects. */
function midpoint(stations) {
  const sum = stations.reduce(
    (acc, s) => ({ lat: acc.lat + s.latitude, lon: acc.lon + s.longitude }),
    { lat: 0, lon: 0 }
  );
  return { lat: sum.lat / stations.length, lon: sum.lon / stations.length };
}

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

  const [weatherCache, setWeatherCache] = useState({});
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [nearbyStations, setNearbyStations] = useState([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);

  // ── Fetch weather for selected stations ──────
  useEffect(() => {
    if (selectedStations.length === 0) return;

    const toFetch = selectedStations.filter(
      (s) => !weatherCache[s.station_number]
    );
    if (toFetch.length === 0) return;

    let cancelled = false;
    setWeatherLoading(true);

    Promise.all(
      toFetch.map((s) =>
        api
          .get(`/api/stations/${s.station_number}/weather`)
          .then((data) => ({ stationNumber: s.station_number, data }))
          .catch(() => ({ stationNumber: s.station_number, data: null }))
      )
    ).then((results) => {
      if (cancelled) return;
      setWeatherCache((prev) => {
        const next = { ...prev };
        results.forEach((r) => {
          if (r.data) next[r.stationNumber] = r.data;
        });
        return next;
      });
      setWeatherLoading(false);
    });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStations]);

  // ── Fetch nearby stations ────────────────────
  const selectedNumbers = useMemo(
    () => new Set(selectedStations.map((s) => s.station_number)),
    [selectedStations]
  );

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

  // ── Aggregate readings ───────────────────────
  const readingSummary = useMemo(() => {
    const withReading = selectedStations.filter((s) => s.latest_reading);

    const flows = withReading
      .filter((s) => s.latest_reading.discharge != null)
      .map((s) => ({ value: s.latest_reading.discharge, name: s.station_name }));

    // Exclude lake/reservoir stations — their elevation values are on a
    // different scale from river water levels and would skew the average.
    const levels = withReading
      .filter((s) => s.station_type !== "L" && s.latest_reading.water_level != null)
      .map((s) => ({ value: s.latest_reading.water_level, name: s.station_name }));

    const flowRatings = withReading
      .map((s) => s.latest_reading.flow_rating)
      .filter(Boolean);
    const levelRatings = withReading
      .map((s) => s.latest_reading.level_rating)
      .filter(Boolean);

    const avgFlow = flows.length
      ? (flows.reduce((sum, f) => sum + f.value, 0) / flows.length).toFixed(1)
      : null;
    const avgLevel = levels.length
      ? (levels.reduce((sum, l) => sum + l.value, 0) / levels.length).toFixed(1)
      : null;

    const highFlow = flows.length ? flows.reduce((a, b) => (b.value > a.value ? b : a)) : null;
    const lowFlow = flows.length ? flows.reduce((a, b) => (b.value < a.value ? b : a)) : null;
    const highLevel = levels.length ? levels.reduce((a, b) => (b.value > a.value ? b : a)) : null;
    const lowLevel = levels.length ? levels.reduce((a, b) => (b.value < a.value ? b : a)) : null;

    const dominantFlowRating = mode(flowRatings);
    const dominantLevelRating = mode(levelRatings);

    return {
      avgFlow, avgLevel,
      highFlow: highFlow ? { value: highFlow.value.toFixed(1), name: highFlow.name } : null,
      lowFlow: lowFlow ? { value: lowFlow.value.toFixed(1), name: lowFlow.name } : null,
      highLevel: highLevel ? { value: highLevel.value.toFixed(1), name: highLevel.name } : null,
      lowLevel: lowLevel ? { value: lowLevel.value.toFixed(1), name: lowLevel.name } : null,
      dominantFlowRating,
      dominantLevelRating,
    };
  }, [selectedStations]);

  // ── Aggregate weather ────────────────────────
  const weatherSummary = useMemo(() => {
    const entries = selectedStations
      .map((s) => weatherCache[s.station_number])
      .filter(Boolean)
      .map((w) => ({ current: w.weather?.current, name: w.station_number }));

    const temps = entries
      .filter((e) => e.current?.temperature_c != null)
      .map((e) => {
        const station = selectedStations.find((s) => s.station_number === e.name);
        return { value: e.current.temperature_c, name: station?.station_name || e.name };
      });

    const sunrises = entries
      .filter((e) => e.current?.sunrise)
      .map((e) => {
        const station = selectedStations.find((s) => s.station_number === e.name);
        return { value: e.current.sunrise, name: station?.station_name || e.name };
      });

    const sunsets = entries
      .filter((e) => e.current?.sunset)
      .map((e) => {
        const station = selectedStations.find((s) => s.station_number === e.name);
        return { value: e.current.sunset, name: station?.station_name || e.name };
      });

    const avgTemp = temps.length
      ? (temps.reduce((sum, t) => sum + t.value, 0) / temps.length).toFixed(1)
      : null;

    const highTemp = temps.length ? temps.reduce((a, b) => (b.value > a.value ? b : a)) : null;
    const lowTemp = temps.length ? temps.reduce((a, b) => (b.value < a.value ? b : a)) : null;

    // Earliest sunrise, latest sunset
    const earliestSunrise = sunrises.length
      ? sunrises.reduce((a, b) => (a.value < b.value ? a : b))
      : null;
    const latestSunset = sunsets.length
      ? sunsets.reduce((a, b) => (a.value > b.value ? a : b))
      : null;

    return {
      avgTemp,
      highTemp: highTemp ? { value: highTemp.value.toFixed(1), name: highTemp.name } : null,
      lowTemp: lowTemp ? { value: lowTemp.value.toFixed(1), name: lowTemp.name } : null,
      earliestSunrise,
      latestSunset,
      loadedCount: entries.length,
    };
  }, [selectedStations, weatherCache]);

  // ── Nearby stations not already selected ─────
  const filteredNearby = useMemo(
    () => nearbyStations.filter((s) => !selectedNumbers.has(s.station_number)),
    [nearbyStations, selectedNumbers]
  );

  // Don't render if nothing selected
  if (selectedStations.length === 0) return null;

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10 h-1/3 overflow-y-auto bg-white rounded-t-lg shadow-lg border border-slate-200 md:bottom-auto md:left-auto md:top-3 md:right-3 md:h-auto md:w-80 md:max-h-[calc(100%-24px)] md:rounded-lg">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-slate-100 px-4 py-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          Selection ({selectedStations.length})
        </h2>
        <button
          onClick={clearSelection}
          className="text-xs text-red-500 hover:text-red-700 font-medium transition-colors cursor-pointer"
        >
          Clear All
        </button>
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
