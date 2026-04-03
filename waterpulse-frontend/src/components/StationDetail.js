"use client";

import { useState, useEffect, useCallback } from "react";
import RatingPill from "@/components/RatingPill";
import api from "@/lib/api";
import {
  PROVINCES,
  STATION_TYPES,
  DATA_SOURCES,
  WMO_DESCRIPTIONS,
  RATING_CONFIG,
  getAqiCategory,
  getBeaufortScale,
} from "@/lib/constants";

/* ─────────────────────────────────────────────
   StationDetail — shared station content used
   by both the full page and the modal overlay.
   ───────────────────────────────────────────── */

// ── Icons ───────────────────────────────────

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

// ── Helpers ──────────────────────────────────

function PercentileBar({ label, value, percentiles, rating }) {
  if (!percentiles || value == null) return null;

  const { p10, p25, p75, p90 } = percentiles;
  const min = Math.min(p10 * 0.5, value);
  const max = Math.max(p90 * 1.5, value);
  const range = max - min || 1;

  const toPercent = (v) => Math.max(0, Math.min(100, ((v - min) / range) * 100));

  const ratingConfig = RATING_CONFIG[rating?.toLowerCase()];

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-slate-900">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900">
            {value.toFixed(3)}
          </span>
          {rating && <RatingPill rating={rating} />}
        </div>
      </div>
      <div className="relative h-2.5 rounded-full bg-slate-100 overflow-hidden">
        {/* P25-P75 "average" zone */}
        <div
          className="absolute top-0 h-full bg-emerald-100 rounded-full"
          style={{
            left: `${toPercent(p25)}%`,
            width: `${toPercent(p75) - toPercent(p25)}%`,
          }}
        />
        {/* Current value marker */}
        <div
          className={`absolute top-0 h-full w-1.5 rounded-full ${ratingConfig?.dot || "bg-slate-400"}`}
          style={{ left: `${toPercent(value)}%` }}
        />
      </div>
      <div className="flex justify-between mt-1 text-[10px] text-slate-300">
        <span>P10: {p10.toFixed(1)}</span>
        <span>Median: {percentiles.p50.toFixed(1)}</span>
        <span>P90: {p90.toFixed(1)}</span>
      </div>
    </div>
  );
}

function StatBlock({ label, value, unit, sub, decimals = 3 }) {
  return (
    <div className="text-center p-3">
      <div className="text-xs text-slate-900 mb-1">{label}</div>
      <div className="text-lg font-semibold text-slate-900">
        {value != null ? (
          <>
            {typeof value === "number" ? value.toFixed(decimals) : value}
            {unit && <span className="text-sm font-normal text-slate-900 ml-0.5">{unit}</span>}
          </>
        ) : (
          <span className="text-slate-300">—</span>
        )}
      </div>
      {sub && <div className="text-[10px] text-slate-900 mt-0.5">{sub}</div>}
    </div>
  );
}


/**
 * StationDetail — renders the full station content.
 *
 * Props:
 *   stationNumber — the station ID to fetch
 *   onClose       — called when the user clicks the back/close button
 *                    (optional — if not provided, back button is hidden)
 *   refreshButton — whether to show the refresh button (default true)
 */
export default function StationDetail({ stationNumber, onClose, refreshButton = true }) {
  const [station, setStation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Weather is fetched separately from its own cached endpoint
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);

  // ── Fetch station + reading ───────────────
  const loadStation = useCallback(async () => {
    try {
      const data = await api.get(`/api/stations/${stationNumber}/current`);
      setStation(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [stationNumber]);

  // ── Fetch weather (cached, on-demand) ─────
  const loadWeather = useCallback(async () => {
    setWeatherLoading(true);
    try {
      const data = await api.get(`/api/stations/${stationNumber}/weather`);
      setWeather(data.weather);
    } catch (err) {
      console.error("Weather fetch failed:", err);
    } finally {
      setWeatherLoading(false);
    }
  }, [stationNumber]);

  useEffect(() => { loadStation(); }, [loadStation]);

  // Fetch weather once the station is loaded and has coordinates
  useEffect(() => {
    if (station?.latitude && station?.longitude) {
      loadWeather();
    }
  }, [station?.latitude, station?.longitude, loadWeather]);

  // Auto-refresh removed — the backend scheduler keeps data fresh.
  // Users can still manually refresh via the refresh button.

  // ── Refresh this station's reading ────────
  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await api.post(
        `/api/readings/refresh?station_numbers=${stationNumber}`
      );
      await loadStation();
      loadWeather();
    } catch (err) {
      console.error("Refresh failed:", err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <IconLoader className="w-6 h-6 text-[#2196f3]" />
        <span className="ml-2 text-sm text-slate-900">Loading station...</span>
      </div>
    );
  }

  if (error || !station) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <p className="text-slate-900">{error || "Station not found"}</p>
        {onClose && (
          <button onClick={onClose} className="text-sm text-[#2196f3] hover:underline">
            &larr; Go back
          </button>
        )}
      </div>
    );
  }

  const reading = station.latest_reading;
  const current = weather?.current;
  const aqi = weather?.air_quality;
  const forecast = weather?.daily_forecast;

  const typeLabel = STATION_TYPES[station.station_type] || station.station_type;
  const isLake = station.station_type === "L";
  const levelLabel = isLake ? "Elevation" : "Level";
  const provinceName = PROVINCES[station.province] || station.province;

  // Backend sends naive UTC timestamps — append Z so JS converts to local timezone
  const toLocalDate = (utc) => utc ? new Date(utc.endsWith("Z") ? utc : utc + "Z") : null;
  const fetchedAt = toLocalDate(reading?.fetched_at);
  const readingTime = toLocalDate(reading?.datetime_utc);

  const aqiInfo = aqi?.us_aqi != null ? getAqiCategory(aqi.us_aqi) : null;
  const weatherDesc = current?.weather_code != null
    ? WMO_DESCRIPTIONS[current.weather_code] : null;

  return (
    <div>
      {/* ── Station header ────────────── */}
      <div className="mb-8">
        <h1 className="font-display text-2xl sm:text-3xl text-slate-900 mb-1">
          {station.station_name}
        </h1>
        <p className="text-sm text-slate-900">
          {station.station_number}
          {typeLabel && <> &middot; {typeLabel}</>}
          {provinceName && <> &middot; {provinceName}</>}
          {reading?.data_source && (
            <> &middot; Source: {DATA_SOURCES[reading.data_source] || reading.data_source}</>
          )}
        </p>
      </div>

      {/* ── Refresh button ───────────── */}
      {refreshButton && (
        <div className="flex justify-end mb-4">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-900 hover:text-[#1e6ba8] hover:border-[#2196f3]/40 disabled:opacity-50 transition-all"
          >
            {refreshing ? <IconLoader className="w-3.5 h-3.5" /> : <IconRefresh className="w-3.5 h-3.5" />}
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      )}

      {/* ── No reading message ────────── */}
      {!reading && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center mb-8">
          <p className="text-slate-900 text-sm mb-3">
            No current reading available for this station.
          </p>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-sm text-[#2196f3] hover:underline"
          >
            Try refreshing
          </button>
        </div>
      )}

      {reading && (
        <div className="space-y-6">

          {/* ── Readings + Ratings card ──── */}
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
              Current Readings
            </h2>

            {/* Stat row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 mb-6 bg-slate-50 rounded-lg">
              <StatBlock label="Flow" value={reading.discharge} unit="m³/s" />
              <StatBlock label={levelLabel} value={reading.water_level} unit="m" />
              {reading.outflow != null && (
                <StatBlock label="Outflow" value={reading.outflow} unit="m³/s" />
              )}
              {reading.pct_full != null && (
                <StatBlock label="Capacity" value={reading.pct_full} unit="%" decimals={1} />
              )}
            </div>

            {/* Percentile bars */}
            <PercentileBar
              label="Flow"
              value={reading.discharge}
              percentiles={reading.flow_percentiles}
              rating={reading.flow_rating}
            />
            <PercentileBar
              label={levelLabel}
              value={reading.water_level}
              percentiles={reading.level_percentiles}
              rating={reading.level_rating}
            />

            {isLake && reading.pct_full != null && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-medium text-slate-900">Capacity</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-900">
                      {reading.pct_full.toFixed(1)}%
                    </span>
                    {reading.pct_full_rating && <RatingPill rating={reading.pct_full_rating} />}
                  </div>
                </div>
                <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      reading.pct_full < 20
                        ? "bg-red-400"
                        : reading.pct_full < 40
                          ? "bg-amber-400"
                          : reading.pct_full <= 70
                            ? "bg-emerald-400"
                            : reading.pct_full <= 90
                              ? "bg-blue-400"
                              : "bg-purple-400"
                    }`}
                    style={{ width: `${Math.min(reading.pct_full, 100)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Timestamp */}
            <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-900">
              {readingTime && (
                <span>Reading: {readingTime.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</span>
              )}
              {fetchedAt && (
                <span>Updated: {fetchedAt.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</span>
              )}
            </div>
          </div>

          {/* ── Weather card ──────────────── */}
          {weatherLoading && !current && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 flex items-center justify-center py-12">
              <IconLoader className="w-5 h-5 text-[#2196f3]" />
              <span className="ml-2 text-sm text-slate-900">Loading weather...</span>
            </div>
          )}
          {current && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
                Weather &amp; Air Quality
              </h2>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 mb-4 bg-slate-50 rounded-lg">
                <StatBlock
                  label="Temperature"
                  value={current.temperature_c}
                  unit="°C"
                  decimals={1}
                  sub={current.apparent_temperature_c != null ? `Feels like ${current.apparent_temperature_c.toFixed(1)}°C` : null}
                />
                {(() => {
                  const beaufort = getBeaufortScale(current.wind_speed_kmh);
                  return (
                    <StatBlock
                      label="Wind"
                      value={current.wind_speed_kmh}
                      unit="km/h"
                      decimals={1}
                      sub={[
                        current.wind_gusts_kmh != null ? `Gusts ${current.wind_gusts_kmh.toFixed(0)} km/h` : null,
                        beaufort ? `Beaufort ${beaufort.force} — ${beaufort.label}` : null,
                      ].filter(Boolean).join(" · ") || null}
                    />
                  );
                })()}
                <StatBlock
                  label="Air Quality Index"
                  value={aqi?.us_aqi}
                  decimals={0}
                  sub={aqiInfo ? aqiInfo.label : null}
                />
                <StatBlock
                  label="UV Index"
                  value={current.uv_index}
                  decimals={0}
                />
              </div>

              {/* Weather description */}
              <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-900">
                {weatherDesc && (
                  <span>{weatherDesc}</span>
                )}
                {current.sunrise && (
                  <span>
                    Sunrise: {new Date(current.sunrise).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                  </span>
                )}
                {current.sunset && (
                  <span>
                    Sunset: {new Date(current.sunset).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                  </span>
                )}                
                {current.humidity_pct != null && (
                  <span>Humidity: {current.humidity_pct.toFixed(0)}%</span>
                )}
                {current.visibility_m != null && (
                  <span>
                    Visibility: {(current.visibility_m / 1000).toFixed(1)} km
                  </span>
                )}
              </div>
            </div>
          )}

          {/* ── 7-day forecast card ──────── */}
          {forecast && forecast.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
                7-Day Forecast
              </h2>

              <div className="overflow-x-auto -mx-2">
                <div className="flex gap-2 px-2 min-w-max">
                  {forecast.map((day) => {
                    const dayName = new Date(day.date + "T12:00:00").toLocaleDateString("en-CA", {
                      weekday: "short",
                    });
                    const desc = day.weather_code != null
                      ? WMO_DESCRIPTIONS[day.weather_code] : null;

                    return (
                      <div
                        key={day.date}
                        className="flex flex-col items-center text-center p-3 rounded-lg bg-slate-50 min-w-[80px]"
                      >
                        <span className="text-xs font-medium text-slate-900 mb-1">
                          {dayName}
                        </span>
                        <span className="text-sm font-semibold text-slate-900">
                          {day.temperature_max_c != null ? `${day.temperature_max_c.toFixed(0)}°` : "—"}
                        </span>
                        <span className="text-[10px] text-slate-900">
                          {day.temperature_min_c != null ? `${day.temperature_min_c.toFixed(0)}°` : ""}
                        </span>
                        {desc && (
                          <span className="text-[10px] text-slate-900 mt-1 leading-tight">
                            {desc}
                          </span>
                        )}
                        {day.precipitation_sum_mm != null && day.precipitation_sum_mm > 0 && (
                          <span className="text-[10px] text-blue-500 mt-0.5">
                            {day.precipitation_sum_mm.toFixed(1)} mm
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── Station metadata card ────── */}
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider mb-4">
              Station Information
            </h2>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-3 text-sm">
              {[
                ["Station Number", station.station_number],
                ["Type", typeLabel],
                ["Province", provinceName],
                ["Data Source", reading?.data_source ? (DATA_SOURCES[reading.data_source] || reading.data_source) : (DATA_SOURCES[station.data_source] || station.data_source)],
                ["Basin", station.basin_number],
                ["Catchment", station.catchment_number],
                ["Drainage Basin", station.drainage_basin_prefix],
                ["Latitude", station.latitude?.toFixed(5)],
                ["Longitude", station.longitude?.toFixed(5)],
                ["Reservoir Tracking", station.has_capacity ? "Yes" : "No"],
              ]
                .filter(([, val]) => val != null && val !== "No" && val !== false)
                .map(([label, val]) => (
                  <div key={label}>
                    <dt className="text-slate-900 text-xs">{label}</dt>
                    <dd className="text-slate-900 font-medium">{val}</dd>
                  </div>
                ))}
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}
