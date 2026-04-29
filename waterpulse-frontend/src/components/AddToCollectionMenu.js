"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/context/authcontext";

const IconStar = ({ filled, className = "w-4 h-4" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
  </svg>
);

const IconCheck = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const IconLoader = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={`${className} animate-spin`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" className="opacity-25" />
    <path d="M4 12a8 8 0 018-8" className="opacity-75" />
  </svg>
);

const IconPlus = ({ className = "w-3.5 h-3.5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

/**
 * Star button on a station card that opens a popover for adding the station
 * to one or more of the user's collections (or creating a new one).
 *
 * Hidden entirely for guests — sign-up to save stations is messaged
 * elsewhere (the /collections page header). For signed-in users, the icon
 * is hollow until any collection contains this station.
 *
 * The membership lookup is intentionally on-demand: we only fetch
 * collection memberships when the popover opens. A lighter
 * station-list-with-memberships endpoint is a known follow-up — see the
 * scheduled review job in the session log — to replace the per-detail
 * Promise.all once a user accumulates many collections.
 *
 * Props:
 *   stationNumber  — the station to add/remove
 *   variant        — visual size: "sm" | "md" (default "md")
 */
export default function AddToCollectionMenu({ stationNumber, variant = "md" }) {
  const { isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [collections, setCollections] = useState([]); // [{ id, name, contains }]
  const [pendingIds, setPendingIds] = useState(new Set());

  const containerRef = useRef(null);
  const buttonRef = useRef(null);

  const containsAny = collections.some((c) => c.contains);

  // Load membership when the popover opens (per-station)
  useEffect(() => {
    if (!open || !isAuthenticated) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        // 1. List the user's collections
        const summaries = await api.get("/api/collections/");
        // Only collections this user can add stations to (owner or editor)
        const editable = summaries.filter(
          (c) => c.role === "owner" || c.role === "editor" || c.role === "superuser"
        );
        if (editable.length === 0) {
          if (!cancelled) {
            setCollections([]);
            setLoading(false);
          }
          return;
        }
        // 2. Fetch each one's stations to check membership.
        // Fine for typical small collection counts; a dedicated
        // collections-by-station endpoint is a known follow-up.
        const details = await Promise.all(
          editable.map((c) =>
            api
              .get(`/api/collections/${c.id}`)
              .then((d) => ({
                id: c.id,
                name: c.name,
                role: c.role,
                contains: (d.stations || []).some(
                  (s) => s.station_number === stationNumber
                ),
              }))
              .catch(() => ({
                id: c.id,
                name: c.name,
                role: c.role,
                contains: false,
              }))
          )
        );
        if (!cancelled) {
          setCollections(details);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.message || "Could not load collections");
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, isAuthenticated, stationNumber]);

  // Close on outside click or Escape
  useEffect(() => {
    if (!open) return;
    const onPointer = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!isAuthenticated) return null;

  const toggleMembership = async (collection) => {
    if (pendingIds.has(collection.id)) return;
    setPendingIds((prev) => new Set(prev).add(collection.id));

    // Optimistic flip
    setCollections((prev) =>
      prev.map((c) =>
        c.id === collection.id ? { ...c, contains: !c.contains } : c
      )
    );

    try {
      if (collection.contains) {
        await api.del(
          `/api/collections/${collection.id}/stations/${stationNumber}`
        );
      } else {
        await api.post(`/api/collections/${collection.id}/stations`, {
          station_numbers: [stationNumber],
        });
      }
    } catch (err) {
      // Revert on failure
      setCollections((prev) =>
        prev.map((c) =>
          c.id === collection.id ? { ...c, contains: collection.contains } : c
        )
      );
      setError(err?.message || "Could not update collection");
    } finally {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(collection.id);
        return next;
      });
    }
  };

  const sizeClasses =
    variant === "sm"
      ? "p-1.5"
      : "p-2";
  const iconClass = variant === "sm" ? "w-3.5 h-3.5" : "w-4 h-4";

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        ref={buttonRef}
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((prev) => !prev);
        }}
        title={containsAny ? "In one or more collections" : "Add to a collection"}
        className={`${sizeClasses} rounded-full transition-colors cursor-pointer ${
          containsAny
            ? "text-amber-500 hover:bg-amber-50"
            : "text-slate-400 hover:text-amber-500 hover:bg-slate-100"
        }`}
      >
        <IconStar filled={containsAny} className={iconClass} />
      </button>

      {open && (
        <div
          className="absolute right-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-slate-200 z-50 overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-3 py-2 border-b border-slate-100">
            <p className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
              Add to collection
            </p>
          </div>

          {loading ? (
            <div className="px-3 py-4 text-xs text-slate-500 flex items-center gap-2">
              <IconLoader />
              Loading collections…
            </div>
          ) : error ? (
            <div className="px-3 py-3 text-xs text-red-600">{error}</div>
          ) : collections.length === 0 ? (
            <div className="px-3 py-3 text-xs text-slate-500">
              You don&apos;t have any collections yet.
            </div>
          ) : (
            <ul className="max-h-64 overflow-y-auto divide-y divide-slate-100">
              {collections.map((collection) => {
                const busy = pendingIds.has(collection.id);
                return (
                  <li key={collection.id}>
                    <button
                      type="button"
                      onClick={() => toggleMembership(collection)}
                      disabled={busy}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-slate-50 transition-colors cursor-pointer disabled:opacity-60"
                    >
                      <span
                        className={`flex items-center justify-center w-4 h-4 rounded border transition-colors ${
                          collection.contains
                            ? "bg-[#2196f3] border-[#2196f3] text-white"
                            : "border-slate-300"
                        }`}
                      >
                        {collection.contains && <IconCheck className="w-3 h-3" />}
                      </span>
                      <span className="flex-1 min-w-0 truncate text-slate-900">
                        {collection.name}
                      </span>
                      {busy && <IconLoader />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <Link
            href={`/collections/new?stations=${encodeURIComponent(stationNumber)}`}
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm border-t border-slate-100 bg-slate-50 hover:bg-slate-100 text-[#1e6ba8] font-medium cursor-pointer"
          >
            <IconPlus />
            New collection with this station
          </Link>
        </div>
      )}
    </div>
  );
}
