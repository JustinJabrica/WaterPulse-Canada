"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

/**
 * Batch-fetch per-station weather and cache it across renders. Backs the
 * map's SelectionSummaryPanel and the collection detail page so they share
 * one fetch + cache pattern instead of duplicating the loop.
 *
 * Usage:
 *   const { weatherCache, loading } = useStationWeatherBatch(stations);
 *
 * Invariants:
 *   - One GET /api/stations/{number}/weather per station that hasn't been
 *     fetched yet during this hook's lifetime. Previously-fetched entries
 *     stay in the cache when `stations` shrinks or shuffles.
 *   - Failed fetches don't enter the cache, so they'll be retried if the
 *     same station appears in a future render.
 *   - The dependency array intentionally includes only `stations` — adding
 *     `weatherCache` would re-run the effect on every successful fetch
 *     (since the cache is what we just updated) and loop forever.
 */
export default function useStationWeatherBatch(stations) {
  const [weatherCache, setWeatherCache] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!stations || stations.length === 0) {
      setLoading(false);
      return;
    }

    const toFetch = stations.filter((s) => !weatherCache[s.station_number]);
    if (toFetch.length === 0) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

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
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stations]);

  return { weatherCache, loading };
}
