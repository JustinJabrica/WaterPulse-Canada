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
import { useAuth } from "@/context/authcontext";

const ROLE_LABEL = {
  owner: "Owner",
  editor: "Editor",
  viewer: "Viewer",
  superuser: "Admin",
};

const IconLock = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const IconGlobe = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="2" y1="12" x2="22" y2="12" />
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
  </svg>
);

const IconStar = ({ filled, className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
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

export default function CollectionDetailPage() {
  const { id } = useParams();
  const { user, isAuthenticated } = useAuth();
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [favouritePending, setFavouritePending] = useState(false);
  const [valuablePending, setValuablePending] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);

    api
      .get(`/api/collections/${id}`)
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
  }, [id]);

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

  const isOwner =
    collection?.role === "owner" || collection?.role === "superuser";
  const canEdit = isOwner || collection?.role === "editor";

  const toggleValuable = async () => {
    if (!collection || valuablePending) return;
    const wasValuable = collection.is_valuable;
    setValuablePending(true);
    try {
      const updated = await api.patch(
        `/api/collections/${collection.id}/valuable`,
        { is_valuable: !wasValuable }
      );
      setCollection(updated);
    } catch (err) {
      setError({ status: err.status, message: err.message });
    } finally {
      setValuablePending(false);
    }
  };

  const toggleFavourite = async () => {
    if (!collection || favouritePending) return;
    const wasFavourited = collection.is_favourited;
    setFavouritePending(true);
    // Optimistic flip
    setCollection({ ...collection, is_favourited: !wasFavourited });
    try {
      if (wasFavourited) {
        await api.del(`/api/collections/${collection.id}/favourite`);
      } else {
        await api.post(`/api/collections/${collection.id}/favourite`);
      }
    } catch (err) {
      // Revert on failure
      setCollection({ ...collection, is_favourited: wasFavourited });
      setError({ status: err.status, message: err.message });
    } finally {
      setFavouritePending(false);
    }
  };

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

  if (error) {
    return <CollectionError status={error.status} message={error.message} />;
  }

  if (!collection) return null;

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/collections"
          className="text-sm text-[#1e6ba8] hover:text-[#0f2a44] inline-flex items-center gap-1"
        >
          ← Back to collections
        </Link>

        <div className="mt-3 flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-3xl font-display text-slate-900 break-words">
                {collection.name}
              </h1>
              <span
                title={collection.is_public ? "Public" : "Private"}
                className="text-slate-400"
              >
                {collection.is_public ? <IconGlobe /> : <IconLock />}
              </span>
              {collection.is_valuable && (
                <span
                  title="Featured collection"
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium"
                >
                  <IconStar filled className="w-3 h-3" />
                  Featured
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              by{" "}
              <span className="font-medium text-slate-700">
                {collection.owner_username}
              </span>
              {collection.role && (
                <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
                  {ROLE_LABEL[collection.role] || collection.role}
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {user?.is_admin && (
              <button
                type="button"
                onClick={toggleValuable}
                disabled={valuablePending}
                title={
                  collection.is_valuable
                    ? "Remove from Featured"
                    : "Mark as Featured"
                }
                className={`p-2 rounded-lg border transition-colors cursor-pointer disabled:opacity-60 ${
                  collection.is_valuable
                    ? "bg-amber-50 border-amber-200 text-amber-600 hover:bg-amber-100"
                    : "bg-white border-slate-300 text-slate-400 hover:text-amber-600 hover:bg-slate-50"
                }`}
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill={collection.is_valuable ? "currentColor" : "none"}
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              </button>
            )}
            {isAuthenticated && (
              <button
                type="button"
                onClick={toggleFavourite}
                disabled={favouritePending}
                title={
                  collection.is_favourited
                    ? "Remove from favourites"
                    : "Add to favourites"
                }
                className={`p-2 rounded-lg border transition-colors cursor-pointer disabled:opacity-60 ${
                  collection.is_favourited
                    ? "bg-rose-50 border-rose-200 text-rose-500 hover:bg-rose-100"
                    : "bg-white border-slate-300 text-slate-400 hover:text-rose-500 hover:bg-slate-50"
                }`}
              >
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill={collection.is_favourited ? "currentColor" : "none"}
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
              </button>
            )}
            {stations.length > 0 && (
              <Link
                href={`/map?collection=${collection.id}`}
                className="px-3 py-1.5 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-300 hover:bg-slate-100 transition-colors"
              >
                View on Map
              </Link>
            )}
            {canEdit && (
              <Link
                href={`/collections/${collection.id}/edit`}
                className="px-3 py-1.5 rounded-lg bg-[#2196f3] text-white text-sm font-medium hover:bg-[#1e6ba8] transition-colors"
              >
                Edit
              </Link>
            )}
          </div>
        </div>

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
      </div>

      {/* Aggregation panels */}
      {stations.length > 0 ? (
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
              <p className="text-sm text-slate-400 py-2">
                Loading weather data…
              </p>
            ) : (
              <p className="text-sm text-slate-400 py-2">
                No weather data available
              </p>
            )}
          </section>
        </div>
      ) : null}

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

      {/* Collaborators (owner + collaborators only) */}
      {collection.collaborators?.length > 0 &&
        (isOwner || collection.role === "editor" || collection.role === "viewer") && (
          <section className="bg-white rounded-xl border border-slate-200 p-4 mb-8">
            <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2">
              Collaborators
            </h2>
            <ul className="divide-y divide-slate-100">
              {collection.collaborators.map((c) => (
                <li
                  key={c.user_id}
                  className="py-2 flex items-center justify-between"
                >
                  <span className="text-sm text-slate-700">{c.username}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
                    {c.permission === "edit" ? "Editor" : "Viewer"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

      {/* Share link (owner-only) */}
      {isOwner && (
        <section className="bg-white rounded-xl border border-slate-200 p-4 mb-8">
          <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2">
            Share link
          </h2>
          {collection.share_token ? (
            <code className="block text-xs bg-slate-50 border border-slate-200 rounded px-2 py-2 break-all text-slate-700">
              {`${typeof window !== "undefined" ? window.location.origin : ""}/collections/share/${collection.share_token}`}
            </code>
          ) : (
            <p className="text-sm text-slate-500">
              Sharing is disabled. Open{" "}
              <Link
                href={`/collections/${collection.id}/edit`}
                className="text-[#1e6ba8] hover:text-[#0f2a44] underline"
              >
                Edit
              </Link>{" "}
              to generate a link.
            </p>
          )}
        </section>
      )}
    </main>
  );
}

function CollectionError({ status, message }) {
  if (status === 401) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">Sign in required</h1>
        <p className="mt-2 text-sm text-slate-600">
          This collection is private. Sign in to view it.
        </p>
        <Link
          href="/login"
          className="inline-block mt-4 px-4 py-2 rounded-lg bg-[#2196f3] text-white text-sm font-medium hover:bg-[#1e6ba8]"
        >
          Sign in
        </Link>
      </main>
    );
  }
  if (status === 403) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">No access</h1>
        <p className="mt-2 text-sm text-slate-600">
          You don&apos;t have permission to view this collection.
        </p>
      </main>
    );
  }
  if (status === 404) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">Not found</h1>
        <p className="mt-2 text-sm text-slate-600">
          We couldn&apos;t find a collection with that id.
        </p>
        <Link
          href="/collections"
          className="inline-block mt-4 px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium hover:bg-slate-200"
        >
          Back to collections
        </Link>
      </main>
    );
  }
  return (
    <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
      <h1 className="text-2xl font-display text-slate-900">Something went wrong</h1>
      <p className="mt-2 text-sm text-slate-600">{message}</p>
    </main>
  );
}
