"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/authcontext";
import api from "@/lib/api";
import CollectionEditor from "../CollectionEditor";

/**
 * /collections/new
 *
 * Create a new collection. Supports prefilling from URL params:
 *   ?stations=05AA001,05AA002 — pre-attach stations on submit
 *   ?name=Foo                 — prefill name (used by "Save selection as collection")
 *
 * Wrapped in Suspense because `useSearchParams` triggers a CSR bailout
 * at build time otherwise (Next.js refuses to prerender pages that read
 * search params without a boundary).
 */
export default function NewCollectionPage() {
  return (
    <Suspense fallback={<NewCollectionFallback />}>
      <NewCollectionInner />
    </Suspense>
  );
}

function NewCollectionFallback() {
  return (
    <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 bg-slate-200 rounded" />
        <div className="h-32 bg-slate-200 rounded-xl" />
      </div>
    </main>
  );
}

function NewCollectionInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [stationNumbers, setStationNumbers] = useState([]);
  const [initialName, setInitialName] = useState("");

  useEffect(() => {
    const stations = params.get("stations");
    if (stations) {
      setStationNumbers(stations.split(",").map((s) => s.trim()).filter(Boolean));
    }
    const name = params.get("name");
    if (name) setInitialName(name);
  }, [params]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/login?next=/collections/new");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleSubmit = async (data) => {
    const created = await api.post("/api/collections/", {
      ...data,
      station_numbers: stationNumbers,
    });
    router.push(`/collections/${created.id}`);
  };

  if (authLoading || !isAuthenticated) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-slate-200 rounded" />
          <div className="h-32 bg-slate-200 rounded-xl" />
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      <Link
        href="/collections"
        className="text-sm text-[#1e6ba8] hover:text-[#0f2a44] inline-flex items-center gap-1"
      >
        ← Back to collections
      </Link>

      <h1 className="text-3xl font-display text-slate-900 mt-3 mb-2">
        New collection
      </h1>
      <p className="text-sm text-slate-500 mb-6">
        Group stations together to view aggregated stats, share with others,
        or come back to later.
      </p>

      {stationNumbers.length > 0 && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {stationNumbers.length}{" "}
          {stationNumbers.length === 1 ? "station" : "stations"} from your map
          selection will be added on save.
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <CollectionEditor
          initial={initialName ? { name: initialName } : null}
          onSubmit={handleSubmit}
          onCancel={() => router.push("/collections")}
          submitLabel="Create collection"
        />
      </div>
    </main>
  );
}
