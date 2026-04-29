"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import CollectionEditor from "../../CollectionEditor";
import StationPicker from "../../StationPicker";
import CollaboratorPicker from "../../CollaboratorPicker";
import ShareLinkPanel from "../../ShareLinkPanel";

const IconTrash = ({ className = "w-4 h-4" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    <line x1="10" y1="11" x2="10" y2="17" />
    <line x1="14" y1="11" x2="14" y2="17" />
  </svg>
);

export default function EditCollectionPage() {
  const { id } = useParams();
  const router = useRouter();
  const [collection, setCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const refetch = async () => {
    try {
      const data = await api.get(`/api/collections/${id}`);
      setCollection(data);
    } catch (err) {
      setError({ status: err.status, message: err.message });
    }
  };

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

  const alreadyAdded = useMemo(
    () =>
      new Set((collection?.stations || []).map((s) => s.station_number)),
    [collection]
  );

  const isOwner = collection?.role === "owner" || collection?.role === "superuser";
  const canEdit = isOwner || collection?.role === "editor";

  if (loading) {
    return (
      <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-slate-200 rounded" />
          <div className="h-32 bg-slate-200 rounded-xl" />
        </div>
      </main>
    );
  }

  if (error || !collection) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">
          {error?.status === 404 ? "Not found" : "Could not load collection"}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {error?.message || "Try again later."}
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

  if (!canEdit) {
    return (
      <main className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16 text-center">
        <h1 className="text-2xl font-display text-slate-900">Read-only</h1>
        <p className="mt-2 text-sm text-slate-600">
          You don&apos;t have permission to edit this collection.
        </p>
        <Link
          href={`/collections/${id}`}
          className="inline-block mt-4 px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium hover:bg-slate-200"
        >
          Back to collection
        </Link>
      </main>
    );
  }

  const handleSubmit = async (data) => {
    // Editors can't toggle is_public — strip it before sending.
    const payload = isOwner
      ? data
      : { name: data.name, description: data.description, tags: data.tags };
    await api.patch(`/api/collections/${id}`, payload);
    router.push(`/collections/${id}`);
  };

  const handleAddStation = async (stationNumber) => {
    const updated = await api.post(`/api/collections/${id}/stations`, {
      station_numbers: [stationNumber],
    });
    setCollection(updated);
  };

  const handleRemoveStation = async (stationNumber) => {
    await api.del(`/api/collections/${id}/stations/${stationNumber}`);
    setCollection({
      ...collection,
      stations: collection.stations.filter(
        (s) => s.station_number !== stationNumber
      ),
      station_count: Math.max(0, collection.station_count - 1),
    });
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.del(`/api/collections/${id}`);
      router.push("/collections");
    } catch (err) {
      setError({ status: err.status, message: err.message });
      setDeleting(false);
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16">
      <Link
        href={`/collections/${id}`}
        className="text-sm text-[#1e6ba8] hover:text-[#0f2a44] inline-flex items-center gap-1"
      >
        ← Back to collection
      </Link>

      <h1 className="text-3xl font-display text-slate-900 mt-3 mb-6">
        Edit collection
      </h1>

      {/* Editor */}
      <section className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-4">
          Details
        </h2>
        <CollectionEditor
          initial={collection}
          canEditPublic={isOwner}
          onSubmit={handleSubmit}
          onCancel={() => router.push(`/collections/${id}`)}
          submitLabel="Save changes"
        />
      </section>

      {/* Stations */}
      <section className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
          Stations ({collection.stations?.length ?? 0})
        </h2>

        {collection.stations?.length > 0 ? (
          <ul className="divide-y divide-slate-100 mb-4">
            {collection.stations.map((s) => (
              <li
                key={s.station_number}
                className="flex items-center justify-between gap-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {s.station_name || s.station_number}
                  </p>
                  <p className="text-xs text-slate-500">
                    {s.station_number}
                    {s.province ? ` • ${s.province}` : ""}
                    {s.station_type ? ` • ${s.station_type}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveStation(s.station_number)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-rose-600 hover:bg-rose-50 text-xs font-medium transition-colors cursor-pointer"
                >
                  <IconTrash className="w-3.5 h-3.5" />
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500 mb-4">
            No stations yet — search below to add some.
          </p>
        )}

        <StationPicker alreadyAdded={alreadyAdded} onAdd={handleAddStation} />
      </section>

      {/* Collaborators (owner only) */}
      {isOwner && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
            Collaborators
          </h2>
          <CollaboratorPicker
            collectionId={collection.id}
            collaborators={collection.collaborators || []}
            onChange={refetch}
          />
        </section>
      )}

      {/* Share link (owner only) */}
      {isOwner && (
        <section className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
          <h2 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
            Share link
          </h2>
          <ShareLinkPanel
            collectionId={collection.id}
            shareToken={collection.share_token}
            onChange={refetch}
          />
        </section>
      )}

      {/* Danger zone (owner only) */}
      {isOwner && !collection.is_valuable && (
        <section className="bg-rose-50/40 rounded-xl border border-rose-200 p-5">
          <h2 className="text-xs font-semibold text-rose-700 uppercase tracking-wider mb-2">
            Danger zone
          </h2>
          <p className="text-sm text-slate-600 mb-3">
            Deleting a collection cannot be undone. Stations themselves are not
            deleted.
          </p>
          {confirmDelete ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-rose-700">
                Are you sure?
              </span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="px-3 py-1.5 rounded-lg bg-rose-600 text-white text-sm font-medium hover:bg-rose-700 transition-colors cursor-pointer disabled:opacity-60"
              >
                {deleting ? "Deleting…" : "Yes, delete"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                disabled={deleting}
                className="px-3 py-1.5 rounded-lg bg-white text-slate-700 text-sm font-medium border border-slate-300 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="px-3 py-1.5 rounded-lg bg-white text-rose-600 text-sm font-medium border border-rose-300 hover:bg-rose-50 transition-colors cursor-pointer"
            >
              Delete collection
            </button>
          )}
        </section>
      )}
    </main>
  );
}
