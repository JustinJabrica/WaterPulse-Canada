"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import CollectionCard from "@/components/CollectionCard";

const SHOW_COUNT = 3;

/**
 * Featured Collections strip on the dashboard. Renders nothing if no
 * collections have is_valuable=true. Visible to everyone (auth + guest)
 * since featured collections are public by definition (only public
 * collections can be promoted).
 */
export default function FeaturedCollections() {
  const [featured, setFeatured] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get("/api/collections/discover", {
        params: { featured: true, limit: SHOW_COUNT },
      })
      .then((data) => {
        if (!cancelled) setFeatured(data || []);
      })
      .catch(() => {
        // Swallow — featured strip is non-critical; dashboard loads without it.
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || featured.length === 0) return null;

  return (
    <section className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
          Featured Collections
        </h2>
        <Link
          href="/collections/discover?featured=true"
          className="text-xs text-[#1e6ba8] hover:text-[#0f2a44] font-medium"
        >
          See all →
        </Link>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {featured.map((collection) => (
          <CollectionCard key={collection.id} collection={collection} />
        ))}
      </div>
    </section>
  );
}
