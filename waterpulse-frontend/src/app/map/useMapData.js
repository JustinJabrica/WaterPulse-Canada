import { useState, useEffect, useRef } from "react";
import useMapStore from "@/stores/mapStore";
import api from "@/lib/api";

const DEBOUNCE_MS = 300;

/**
 * Fetches stations from the bbox endpoint whenever the map viewport changes.
 *
 * The moveend listener is attached once (when the map loads) and never
 * re-attached. Filter values are read from refs at fetch time so the
 * listener closure is always current — no stale-closure issues.
 */
export default function useMapData(mapRef) {
  const provinceFilter = useMapStore((s) => s.provinceFilter);
  const typeFilter = useMapStore((s) => s.typeFilter);
  const setStations = useMapStore((s) => s.setStations);
  const setIsLoading = useMapStore((s) => s.setIsLoading);
  const setError = useMapStore((s) => s.setError);

  const [mapReady, setMapReady] = useState(false);
  const debounceTimer = useRef(null);

  // Refs so the fetch function always reads current filter values
  // without needing to be recreated (avoids listener detach/reattach).
  const provinceRef = useRef(provinceFilter);
  const typeRef = useRef(typeFilter);
  provinceRef.current = provinceFilter;
  typeRef.current = typeFilter;

  // Stable fetch function — reads filters from refs, never recreated
  const fetchRef = useRef(null);
  fetchRef.current = async () => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const bounds = map.getBounds();
    const params = {
      min_lat: bounds.getSouth(),
      max_lat: bounds.getNorth(),
      min_lon: bounds.getWest(),
      max_lon: bounds.getEast(),
      limit: 500,
    };

    const province = provinceRef.current;
    const type = typeRef.current;
    if (province) params.province = province;
    if (type !== "all") params.station_type = type;

    setIsLoading(true);
    setError(null);

    try {
      const data = await api.get("/api/stations/bbox", { params });
      setStations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Called by MapView's onLoad
  const fetchForCurrentView = () => {
    setMapReady(true);
  };

  // Attach moveend listener once when map is ready — never re-attaches
  useEffect(() => {
    if (!mapReady) return;

    const map = mapRef.current?.getMap();
    if (!map) return;

    // Initial fetch
    fetchRef.current();

    const handleMoveEnd = () => {
      clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => fetchRef.current(), DEBOUNCE_MS);
    };
    map.on("moveend", handleMoveEnd);

    return () => {
      clearTimeout(debounceTimer.current);
      map.off("moveend", handleMoveEnd);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapReady]);

  // Re-fetch when filters change
  useEffect(() => {
    if (!mapReady) return;
    fetchRef.current();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provinceFilter, typeFilter, mapReady]);

  return { fetchForCurrentView };
}
