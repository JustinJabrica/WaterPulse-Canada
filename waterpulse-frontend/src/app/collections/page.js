"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/authcontext";
import api from "@/lib/api";
import CollectionCard from "@/components/CollectionCard";

const TABS = [
  { key: "mine", label: "Mine" },
  { key: "shared", label: "Shared with me" },
  { key: "favourited", label: "Favourited" },
];

function pickTab(collections, tab) {
  switch (tab) {
    case "mine":
      return collections.filter(
        (c) => c.role === "owner" || c.role === "superuser"
      );
    case "shared":
      return collections.filter(
        (c) => c.role === "editor" || c.role === "viewer"
      );
    case "favourited":
      return collections.filter((c) => c.is_favourited);
    default:
      return collections;
  }
}

function tabCounts(collections) {
  return TABS.reduce((acc, tab) => {
    acc[tab.key] = pickTab(collections, tab.key).length;
    return acc;
  }, {});
}

export default function CollectionsListPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("mine");

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      // Guests see the page but tabs render sign-up CTAs; no fetch.
      setCollections([]);
      return;
    }

    let cancelled = false;
    setLoading(true);
    api
      .get("/api/collections/")
      .then((data) => {
        if (cancelled) return;
        setCollections(data);
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
  }, [authLoading, isAuthenticated]);

  const counts = useMemo(() => tabCounts(collections), [collections]);
  const visible = useMemo(
    () => pickTab(collections, activeTab),
    [collections, activeTab]
  );

  if (authLoading || (loading && collections.length === 0)) {
    return (
      <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-slate-200 rounded" />
          <div className="h-10 w-64 bg-slate-200 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-slate-200 rounded-xl" />
            ))}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-display text-slate-900">Collections</h1>
          <p className="text-sm text-slate-500 mt-1">
            Saved groupings of stations — yours, shared with you, and favourited.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/collections/discover"
            className="px-4 py-2 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-300 hover:bg-slate-100 transition-colors"
          >
            Discover
          </Link>
          {isAuthenticated && (
            <Link
              href="/collections/new"
              className="px-4 py-2 rounded-lg bg-[#2196f3] text-white text-sm font-semibold hover:bg-[#1e6ba8] transition-colors shadow-sm"
            >
              + New collection
            </Link>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-slate-200">
        {TABS.map((tab) => {
          const isActive = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
                isActive
                  ? "text-[#1e6ba8] border-[#2196f3]"
                  : "text-slate-500 border-transparent hover:text-slate-900"
              }`}
            >
              {tab.label}
              {isAuthenticated && (
                <span
                  className={`ml-2 inline-flex items-center justify-center min-w-[1.5rem] px-1.5 py-0.5 rounded-full text-xs ${
                    isActive
                      ? "bg-[#2196f3] text-white"
                      : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {counts[tab.key] ?? 0}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Body */}
      {!isAuthenticated ? (
        <GuestCTA tab={activeTab} />
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState tab={activeTab} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      )}
    </main>
  );
}

function EmptyState({ tab }) {
  const messages = {
    mine: "You haven't created any collections yet.",
    shared: "Nothing has been shared with you yet.",
    favourited: "You haven't favourited any collections yet.",
  };
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
      <p className="text-sm text-slate-600">{messages[tab]}</p>
    </div>
  );
}

function GuestCTA({ tab }) {
  const copy = {
    mine: {
      title: "Create an account to save collections",
      body: "Group your favourite rivers, lakes, and reservoirs into named collections you can share, browse, and view aggregated stats for.",
    },
    shared: {
      title: "Sign in to see collections shared with you",
      body: "Friends and colleagues can invite you to view or co-edit their collections. Sign in to see anything that's been shared.",
    },
    favourited: {
      title: "Sign in to favourite public collections",
      body: "Bookmark public collections you find interesting so they're easy to come back to.",
    },
  }[tab];

  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
      <h2 className="text-lg font-semibold text-slate-900">{copy.title}</h2>
      <p className="text-sm text-slate-600 mt-2 max-w-xl mx-auto">{copy.body}</p>
      <div className="mt-5 flex items-center justify-center gap-2">
        <Link
          href="/register"
          className="px-4 py-2 rounded-lg bg-[#2196f3] text-white text-sm font-medium hover:bg-[#1e6ba8] transition-colors"
        >
          Create an account
        </Link>
        <Link
          href="/login"
          className="px-4 py-2 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-300 hover:bg-slate-100 transition-colors"
        >
          Sign in
        </Link>
      </div>
    </div>
  );
}
