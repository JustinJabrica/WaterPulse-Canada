"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import MapLegend from "./MapLegend";
import SelectionSummaryPanel from "./SelectionSummaryPanel";
import useMapStore from "@/stores/mapStore";
import api from "@/lib/api";
import { stationsBounds } from "@/lib/aggregateStations";

/* MapView uses MapLibre GL JS which requires browser APIs (canvas, WebGL).
   Dynamic import with ssr: false prevents Next.js from attempting to render
   it on the server, where those APIs don't exist. */
const MapView = dynamic(() => import("./MapView"), { ssr: false });

/**
 * Reads URL search params on mount to restore map state from a shared link.
 * Writes back to the URL (via replaceState) when viewport or filters change,
 * so the URL always reflects the current map view without triggering re-renders.
 *
 * Supported params: lat, lng, z, province, type, favourites, collection
 */
function useUrlStateSync() {
  const viewState = useMapStore((s) => s.viewState);
  const provinceFilter = useMapStore((s) => s.provinceFilter);
  const typeFilter = useMapStore((s) => s.typeFilter);
  const favouritesOnly = useMapStore((s) => s.favouritesOnly);
  const collectionFilter = useMapStore((s) => s.collectionFilter);
  const setViewState = useMapStore((s) => s.setViewState);
  const setProvinceFilter = useMapStore((s) => s.setProvinceFilter);
  const setTypeFilter = useMapStore((s) => s.setTypeFilter);
  const setFavouritesOnly = useMapStore((s) => s.setFavouritesOnly);
  const setCollectionFilter = useMapStore((s) => s.setCollectionFilter);

  const initialised = useRef(false);

  // Read from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const lat = parseFloat(params.get("lat"));
    const lng = parseFloat(params.get("lng"));
    const z = parseFloat(params.get("z"));
    const province = params.get("province");
    const type = params.get("type");
    const favourites = params.get("favourites");
    const collection = params.get("collection");

    if (!isNaN(lat) && !isNaN(lng) && !isNaN(z)) {
      setViewState({ latitude: lat, longitude: lng, zoom: z });
    }
    if (province) setProvinceFilter(province.toUpperCase());
    if (type && ["R", "L"].includes(type.toUpperCase())) {
      setTypeFilter(type.toUpperCase());
    }
    if (favourites === "true") setFavouritesOnly(true);
    if (collection) setCollectionFilter(collection);

    initialised.current = true;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Write to URL when state changes (after initial restore)
  useEffect(() => {
    if (!initialised.current) return;

    const params = new URLSearchParams();
    params.set("lat", viewState.latitude.toFixed(4));
    params.set("lng", viewState.longitude.toFixed(4));
    params.set("z", viewState.zoom.toFixed(2));
    if (provinceFilter) params.set("province", provinceFilter);
    if (typeFilter !== "all") params.set("type", typeFilter);
    if (favouritesOnly) params.set("favourites", "true");
    if (collectionFilter) params.set("collection", collectionFilter);

    const url = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", url);
  }, [viewState, provinceFilter, typeFilter, favouritesOnly, collectionFilter]);
}

/**
 * When `?collection={id}` is set in the URL, fetch that collection and
 * pre-select its stations on the map. Triggered by the "View on Map"
 * button on the collection detail page. Only fires once per (collectionId,
 * mount) to avoid clobbering a user's later manual selections.
 */
function useCollectionDeepLink() {
  const collectionFilter = useMapStore((s) => s.collectionFilter);
  const lastLoadedRef = useRef(null);

  useEffect(() => {
    if (!collectionFilter) {
      lastLoadedRef.current = null;
      return;
    }
    if (lastLoadedRef.current === collectionFilter) return;
    lastLoadedRef.current = collectionFilter;

    let cancelled = false;
    api
      .get(`/api/collections/${collectionFilter}`)
      .then((collection) => {
        if (cancelled) return;
        const stations = collection?.stations || [];
        if (stations.length === 0) return;

        useMapStore.setState({ selectedStations: stations });

        const bounds = stationsBounds(stations);
        if (!bounds) return;
        const centerLat = (bounds.minLat + bounds.maxLat) / 2;
        const centerLon = (bounds.minLon + bounds.maxLon) / 2;
        const span = Math.max(
          bounds.maxLat - bounds.minLat,
          bounds.maxLon - bounds.minLon
        );
        // Approx zoom from extent — single station → 11, large span → 4
        let zoom = 12;
        if (span > 0.01) zoom = 11;
        if (span > 0.1) zoom = 8;
        if (span > 1) zoom = 6;
        if (span > 5) zoom = 4;
        useMapStore
          .getState()
          .setViewState({ latitude: centerLat, longitude: centerLon, zoom });
      })
      .catch(() => {
        // 404 or 403 — ignore silently; the URL just doesn't resolve to a
        // viewable collection. The user lands on the map normally.
      });

    return () => {
      cancelled = true;
    };
  }, [collectionFilter]);
}

export default function MapPage() {
  useUrlStateSync();
  useCollectionDeepLink();

  return (
    <div className="h-screen flex flex-col pt-16">
      <Navbar />
      <div className="flex-1 relative">
        <MapView />
        <MapLegend />
        <SelectionSummaryPanel />
      </div>
    </div>
  );
}
