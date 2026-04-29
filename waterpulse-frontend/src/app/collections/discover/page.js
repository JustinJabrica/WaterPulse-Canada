"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import api from "@/lib/api";
import CollectionCard from "@/components/CollectionCard";
import { PROVINCES } from "@/lib/constants";

const DEBOUNCE_MS = 600;

const IconSearch = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const IconStar = ({ filled, className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);

export default function DiscoverPage() {
  return (
    <Suspense fallback={<DiscoverFallback />}>
      <DiscoverInner />
    </Suspense>
  );
}

function DiscoverFallback() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-64 bg-slate-200 rounded" />
        <div className="h-12 w-full bg-slate-200 rounded-lg" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-40 bg-slate-200 rounded-xl" />
          ))}
        </div>
      </div>
    </main>
  );
}

function DiscoverInner() {
  const router = useRouter();
  const params = useSearchParams();

  const [province, setProvince] = useState(params.get("province") || "");
  const [tag, setTag] = useState(params.get("tag") || "");
  const [q, setQ] = useState(params.get("q") || "");
  const [featured, setFeatured] = useState(params.get("featured") === "true");

  const [collections, setCollections] = useState([]);
  const [popularTags, setPopularTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const debounceRef = useRef(null);

  // Push filters to URL (debounced for q)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const next = new URLSearchParams();
      if (province) next.set("province", province);
      if (tag) next.set("tag", tag);
      if (q) next.set("q", q);
      if (featured) next.set("featured", "true");
      const path = `/collections/discover${next.toString() ? `?${next}` : ""}`;
      router.replace(path);
    }, DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [province, tag, q, featured, router]);

  // Fetch popular tags once on mount
  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/tags/popular", { params: { limit: 12 } })
      .then((data) => {
        if (!cancelled) setPopularTags(data || []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Fetch collections whenever filters change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const requestParams = {};
    if (province) requestParams.province = province;
    if (tag) requestParams.tag = tag;
    if (q) requestParams.q = q;
    if (featured) requestParams.featured = true;

    api
      .get("/api/collections/discover", { params: requestParams })
      .then((data) => {
        if (cancelled) return;
        setCollections(data || []);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Could not load collections");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [province, tag, q, featured]);

  const provinceOptions = useMemo(
    () =>
      Object.entries(PROVINCES)
        .map(([code, name]) => ({ code, name }))
        .sort((a, b) => a.name.localeCompare(b.name)),
    []
  );

  const hasFilters = province || tag || q || featured;

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-display text-slate-900">
            Discover collections
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Public collections shared by the community.
          </p>
        </div>
        <Link
          href="/collections"
          className="text-sm text-[#1e6ba8] hover:text-[#0f2a44] inline-flex items-center gap-1"
        >
          ← My collections
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Search */}
          <div className="relative md:col-span-2">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
              <IconSearch />
            </span>
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name"
              className="w-full pl-8 pr-3 py-2 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 text-sm"
            />
          </div>

          {/* Province */}
          <select
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50"
          >
            <option value="">All provinces</option>
            {provinceOptions.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Tag chips + featured toggle */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setFeatured(!featured)}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer border ${
              featured
                ? "bg-amber-50 border-amber-200 text-amber-700"
                : "bg-white border-slate-300 text-slate-600 hover:bg-slate-50"
            }`}
          >
            <IconStar filled={featured} className="w-3 h-3" />
            Featured
          </button>
          {popularTags.map((t) => {
            const active = t.name === tag;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTag(active ? "" : t.name)}
                className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors cursor-pointer border ${
                  active
                    ? "bg-[#2196f3] border-[#2196f3] text-white"
                    : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
                }`}
              >
                {t.name}
                <span className="ml-1 text-[10px] opacity-70">
                  {t.collection_count}
                </span>
              </button>
            );
          })}
          {hasFilters && (
            <button
              type="button"
              onClick={() => {
                setProvince("");
                setTag("");
                setQ("");
                setFeatured(false);
              }}
              className="ml-auto text-xs text-slate-500 hover:text-rose-600 transition-colors cursor-pointer"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      {loading && collections.length === 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-40 bg-slate-100 rounded-xl animate-pulse"
            />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : collections.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
          <p className="text-sm text-slate-600">
            {hasFilters
              ? "No public collections match those filters."
              : "No public collections yet — be the first to share one."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {collections.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      )}
    </main>
  );
}
