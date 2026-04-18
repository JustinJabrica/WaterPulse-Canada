"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import Navbar from "@/components/Navbar";
import MapLegend from "./MapLegend";
import SelectionSummaryPanel from "./SelectionSummaryPanel";
import useMapStore from "@/stores/mapStore";

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

  // Write to URL when state changes (after initial restore).
  // Debounced so a pan gesture (~60 viewState updates/sec) coalesces into a
  // single trailing replaceState call. iOS Safari rate-limits replaceState
  // aggressively and terminates the tab when called per-frame.
  useEffect(() => {
    if (!initialised.current) return;

    const handle = setTimeout(() => {
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
    }, 300);

    return () => clearTimeout(handle);
  }, [viewState, provinceFilter, typeFilter, favouritesOnly, collectionFilter]);
}

export default function MapPage() {
  useUrlStateSync();

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
