"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import api from "@/lib/api";
import RatingPill from "@/components/RatingPill";
import {
  computeReadingSummary,
  computeWeatherSummary,
  formatTime,
} from "@/lib/aggregateStations";
import useStationWeatherBatch from "@/lib/useStationWeatherBatch";

const IconLink = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

function SummaryStat({ label, value, unit, high, low, rating }) {
  return (
    <div className="py-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-700">{label}</span>
        <div className="flex items-center gap-2">
          {rating && <RatingPill rating={rating} />}
          <span className="text-sm font-semibold text-slate-900">
            {value != null ? `${value} ${unit}` : "—"}
          </span>
        </div>
      </div>
      {(high || low) && (
        <div className="flex flex-wrap gap-3 mt-1">
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

/**
 * /collections/share/[token]
 *
 * Anonymous-friendly read-only view. Resolves the token to a collection
 * via the rate-limited GET /api/collections/share/{token} endpoint.
 * Anyone with the link can view; sign-in is not required.
 */
export default function SharedCollectionPage() {
  const { token } = useParams();
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    api
      .get(`/api/collections/share/${token}`)
      .then((data) => {
        if (cancelled) return;
        setCollection(data);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError({ status: err.status, message: err.message });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const stations = collection?.stations ?? [];
  const { weatherCache, loading: weatherLoading } =
    useStationWeatherBatch(stations);

  const readingSummary = useMemo(
    () => computeReadingSummary(stations),
    [stations]
  );
  const weatherSummary = useMemo(
    () => computeWeatherSummary(stations, weatherCache),
    [stations, weatherCache]
  );

  if (loading) {
    return (
      <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-slate-200 rounded" />
          <div className="h-4 w-96 bg-slate-200 rounded" />
          <div className="h-48 bg-slate-200 rounded-xl" />
        </div>
      </main>
    );
  }

  if (error || !collection) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">
          {error?.status === 404 ? "Link expired" : "Could not load"}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {error?.status === 404
            ? "The owner may have rotated or disabled this share link."
            : error?.message || "Try again later."}
        </p>
        <Link
          href="/collections/discover"
          className="inline-block mt-4 px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium hover:bg-slate-200"
        >
          Browse public collections
        </Link>
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      {/* Shared-link banner */}
      <div className="mb-4 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
        <IconLink className="w-3 h-3" />
        Shared collection — view-only
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-display text-slate-900 break-words">
          {collection.name}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          by{" "}
          <span className="font-medium text-slate-700">
            {collection.owner_username}
          </span>
        </p>

        {collection.description && (
          <p className="mt-4 text-slate-700 whitespace-pre-line">
            {collection.description}
          </p>
        )}

        {collection.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-4">
            {collection.tags.map((tag) => (
              <span
                key={tag.id}
                className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}

        {stations.length > 0 && (
          <div className="mt-5">
            <Link
              href={`/map?collection=${collection.id}`}
              className="inline-block px-3 py-1.5 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-300 hover:bg-slate-100 transition-colors"
            >
              View on Map
            </Link>
          </div>
        )}
      </div>

      {/* Aggregation panels */}
      {stations.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <section className="bg-white rounded-xl border border-slate-200 p-4">
            <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1">
              Readings
            </h2>
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
          </section>

          <section className="bg-white rounded-xl border border-slate-200 p-4">
            <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1">
              Weather
              {weatherLoading && (
                <span className="ml-2 text-slate-400 text-[11px] font-normal">
                  loading…
                </span>
              )}
            </h2>
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
                  <span className="text-sm text-slate-700">
                    Sunrise (earliest)
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    {weatherSummary.earliestSunrise
                      ? formatTime(weatherSummary.earliestSunrise.value)
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-slate-700">
                    Sunset (latest)
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    {weatherSummary.latestSunset
                      ? formatTime(weatherSummary.latestSunset.value)
                      : "—"}
                  </span>
                </div>
              </>
            ) : weatherLoading ? (
              <p className="text-sm text-slate-400 py-2">Loading weather…</p>
            ) : (
              <p className="text-sm text-slate-400 py-2">No weather data</p>
            )}
          </section>
        </div>
      )}

      {/* Stations */}
      <section className="bg-white rounded-xl border border-slate-200 p-4 mb-8">
        <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
          Stations ({stations.length})
        </h2>
        {stations.length === 0 ? (
          <p className="text-sm text-slate-500 py-2">
            This collection is empty.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {stations.map((s) => (
              <li
                key={s.station_number}
                className="py-2 flex items-center justify-between gap-3"
              >
                <Link
                  href={`/station/${s.station_number}`}
                  className="min-w-0 flex-1 group"
                >
                  <p className="text-sm font-medium text-slate-900 group-hover:text-[#1e6ba8] truncate">
                    {s.station_name || s.station_number}
                  </p>
                  <p className="text-xs text-slate-500">
                    {s.station_number}
                    {s.province ? ` • ${s.province}` : ""}
                    {s.station_type ? ` • ${s.station_type}` : ""}
                  </p>
                </Link>
                <div className="flex items-center gap-2 shrink-0">
                  {s.latest_reading?.flow_rating && (
                    <RatingPill rating={s.latest_reading.flow_rating} />
                  )}
                  {s.latest_reading?.discharge != null && (
                    <span className="text-xs text-slate-600">
                      {s.latest_reading.discharge.toFixed(1)} m³/s
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
