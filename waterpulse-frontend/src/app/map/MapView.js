import { useRef, useCallback, useMemo, useState, useEffect } from "react";
import Map, { Source, Layer, Popup } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import { Protocol } from "pmtiles";
import { layers as pmLayers, namedFlavor } from "@protomaps/basemaps";
import useMapStore from "@/stores/mapStore";
import useMapData from "./useMapData";
import MapStationCard from "@/components/MapStationCard";
import MapFilterPanel from "./MapFilterPanel";
import LocationConsentModal from "./LocationConsentModal";
import { useAuth } from "@/context/authcontext";
import { PROVINCE_BOUNDS, PROVINCE_COLOURS, PROVINCE_LABEL_ANCHORS, PROVINCES } from "@/lib/constants";

// Register the pmtiles:// protocol handler once at module scope so React
// StrictMode's double-invocation in dev doesn't attempt to register twice.
if (typeof window !== "undefined" && !window.__pmtilesRegistered) {
  maplibregl.addProtocol("pmtiles", new Protocol().tile);
  window.__pmtilesRegistered = true;
}

// Province overlay is only active when zoomed out enough to see all of Canada.
const PROVINCE_OVERLAY_MAX_ZOOM = 6;

/* ── Marker colour mapping ───────────────────────────
   Matches RATING_CONFIG from constants.js:
   Very Low = red, Low = amber, Average = emerald,
   High = blue, Very High = purple, No historical data = slate */
const RATING_COLOURS = {
  "very low": "#ef4444",
  low: "#f59e0b",
  average: "#10b981",
  high: "#3b82f6",
  "very high": "#a855f7",
  none: "#94a3b8",
};

// Basemap: self-hosted Protomaps PMTiles when NEXT_PUBLIC_TILES_URL is set,
// CartoDB Voyager as fallback. The fallback keeps the /map page working on
// fresh clones before the ~5–6 GB canada.pmtiles is downloaded.
const PMTILES_URL = process.env.NEXT_PUBLIC_TILES_URL;
const CARTO_FALLBACK =
  "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json";

function buildMapStyle() {
  if (!PMTILES_URL) return CARTO_FALLBACK;
  const flavor = namedFlavor("light");
  const base = pmLayers("protomaps", flavor, { lang: "en" });
  // Override the default water styling so rivers and lakes read as the
  // primary visual element — aligns with the recreational-waterways focus.
  const tuned = base.map((l) => {
    switch (l.id) {
      case "water":
        return { ...l, paint: { ...l.paint, "fill-color": "#6ec5ff" } };
      case "water_river":
        // minzoom 10 keeps a wide view from drawing every river in northern
        // Canada at once. At zoom 9 the line layer was hitting Firefox's slow-
        // script timeout when fitBounds landed on a distant city.
        return {
          ...l,
          minzoom: 10,
          paint: {
            ...l.paint,
            "line-color": "#6ec5ff",
            "line-width": [
              "interpolate", ["exponential", 1.4], ["zoom"],
              10, 1.6,
              12, 2.8,
              14, 4.5,
              18, 9,
            ],
          },
        };
      case "water_stream":
        // Streams must stay >= 13. Below that, the feature count across a
        // continental viewport is enough to crash the renderer.
        return {
          ...l,
          minzoom: 13,
          paint: {
            ...l.paint,
            "line-color": "#1e6ba8",
            "line-width": [
              "interpolate", ["linear"], ["zoom"],
              14, 0.8,
              18, 2.0,
            ],
          },
        };
      // River/stream labels only appear from zoom 11 so the map stays
      // uncluttered when panning across the country.
      case "water_waterway_label":
        return {
          ...l,
          minzoom: 9,
          layout: {
            ...l.layout,
            "text-font": ["Noto Sans Medium"],
            "symbol-spacing": 150,
            "text-size": [
              "interpolate", ["linear"], ["zoom"],
              9, 16,
              12, 20,
              15, 24,
              17, 28,
            ],
          },
          paint: {
            ...l.paint,
            "text-halo-width": 2,
          },
        };
      case "water_label_lakes":
        return {
          ...l,
          minzoom: 9,
          layout: {
            ...l.layout,
            "text-font": ["Noto Sans Medium"],
            "text-size": [
              "interpolate", ["linear"], ["zoom"],
              9, 16,
              12, 20,
              15, 24,
              17, 28,
            ],
          },
          paint: {
            ...l.paint,
            "text-halo-width": 2,
          },
        };
      default:
        return l;
    }
  });
  return {
    version: 8,
    glyphs:
      "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",
    // Without a sprite the layered style references images (townspot, capital,
    // shields, POI icons) that fail to load and spam the console.
    sprite: "https://protomaps.github.io/basemaps-assets/sprites/v4/light",
    sources: {
      protomaps: {
        type: "vector",
        url: `pmtiles://${PMTILES_URL}`,
        attribution:
          '© <a href="https://openstreetmap.org">OpenStreetMap</a>, © <a href="https://protomaps.com">Protomaps</a>',
      },
    },
    layers: tuned,
  };
}

const MAP_STYLE = buildMapStyle();

/* ── MapLibre layer definitions ──────────────────────
   Three layers render on top of a single GeoJSON source:
   1. Cluster circles — brand blue circles sized by point count
   2. Cluster labels — white count text inside cluster circles
   3. Station markers — individual coloured dots by rating */

const clusterLayer = {
  id: "clusters",
  type: "circle",
  minzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  filter: ["has", "point_count"],
  paint: {
    "circle-color": "#1e6ba8",
    "circle-radius": ["step", ["get", "point_count"], 18, 10, 24, 50, 32],
    "circle-stroke-width": 2,
    "circle-stroke-color": "#ffffff",
  },
};

const clusterCountLayer = {
  id: "cluster-count",
  type: "symbol",
  minzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  filter: ["has", "point_count"],
  layout: {
    "text-field": "{point_count_abbreviated}",
    "text-size": 13,
    "text-font": ["Noto Sans Medium"],
  },
  paint: {
    "text-color": "#ffffff",
  },
};

const provinceClusterCircleLayer = {
  id: "province-clusters",
  type: "circle",
  maxzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  paint: {
    "circle-color": "#1e6ba8",
    "circle-radius": [
      "interpolate",
      ["linear"],
      ["get", "count"],
      1, 14,
      50, 20,
      200, 26,
      1000, 34,
    ],
    "circle-stroke-width": 2,
    "circle-stroke-color": "#ffffff",
  },
};

const provinceClusterCountLayer = {
  id: "province-cluster-count",
  type: "symbol",
  maxzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  layout: {
    "text-field": ["get", "countLabel"],
    "text-size": 13,
    "text-font": ["Noto Sans Medium"],
    "text-allow-overlap": true,
  },
  paint: {
    "text-color": "#ffffff",
  },
};

const provinceFillColour = [
  "match",
  ["get", "code"],
  ...Object.entries(PROVINCE_COLOURS).flat(),
  "#2196f3",
];

const provinceFillLayer = {
  id: "province-fills",
  type: "fill",
  maxzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  paint: {
    "fill-color": provinceFillColour,
    "fill-opacity": [
      "case",
      ["boolean", ["feature-state", "hover"], false],
      0.35,
      0.18,
    ],
  },
};

const provinceBorderLayer = {
  id: "province-borders",
  type: "line",
  paint: {
    "line-color": "#1e6ba8",
    "line-width": 1,
    "line-opacity": 0.35,
  },
};

const provinceLabelLayer = {
  id: "province-labels",
  type: "symbol",
  source: "province-label-anchors",
  maxzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  layout: {
    "text-field": ["get", "name"],
    "text-font": ["Noto Sans Medium"],
    "text-size": ["interpolate", ["linear"], ["zoom"], 2, 10, 4, 14],
    "text-allow-overlap": false,
    "text-padding": 4,
    "text-anchor": "bottom",
    "text-offset": [0, -2.8],
  },
  paint: {
    "text-color": "#0d2137",
    "text-halo-color": "rgba(255,255,255,0.9)",
    "text-halo-width": 1.5,
  },
};

const PROVINCE_LABEL_GEOJSON = {
  type: "FeatureCollection",
  features: Object.entries(PROVINCE_LABEL_ANCHORS).map(([code, coords]) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: coords },
    properties: { code, name: PROVINCES[code] },
  })),
};

const stationMarkerLayer = {
  id: "station-markers",
  type: "circle",
  minzoom: PROVINCE_OVERLAY_MAX_ZOOM,
  filter: ["!", ["has", "point_count"]],
  paint: {
    "circle-color": [
      "match",
      ["get", "primaryRating"],
      "very low", RATING_COLOURS["very low"],
      "low", RATING_COLOURS.low,
      "average", RATING_COLOURS.average,
      "high", RATING_COLOURS.high,
      "very high", RATING_COLOURS["very high"],
      RATING_COLOURS.none,
    ],
    "circle-radius": [
      "case",
      ["get", "isSelected"],
      9,
      6,
    ],
    "circle-stroke-width": [
      "case",
      ["get", "isSelected"],
      3,
      1.5,
    ],
    "circle-stroke-color": [
      "case",
      ["get", "isSelected"],
      "#ffffff",
      "rgba(255,255,255,0.6)",
    ],
  },
};

export default function MapView() {
  const mapRef = useRef(null);
  const hoveredProvinceRef = useRef(null);
  const [placeLabelBeforeId, setPlaceLabelBeforeId] = useState(null);

  const viewState = useMapStore((s) => s.viewState);
  const setViewState = useMapStore((s) => s.setViewState);
  const selectedStationNumber = useMapStore((s) => s.selectedStationNumber);
  const setSelectedStationNumber = useMapStore((s) => s.setSelectedStationNumber);
  const stations = useMapStore((s) => s.stations);
  const selectedStations = useMapStore((s) => s.selectedStations);
  const showNoData = useMapStore((s) => s.showNoData);
  const typeFilter = useMapStore((s) => s.typeFilter);
  const provinceFilter = useMapStore((s) => s.provinceFilter);
  const provinceCounts = useMapStore((s) => s.provinceCounts);
  const userLocation = useMapStore((s) => s.userLocation);
  const setUserLocation = useMapStore((s) => s.setUserLocation);
  const locationConsentGranted = useMapStore((s) => s.locationConsentGranted);
  const setLocationConsentGranted = useMapStore((s) => s.setLocationConsentGranted);

  const [consentModalOpen, setConsentModalOpen] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const didAutoPromptRef = useRef(false);
  const { showToast } = useAuth();

  useEffect(() => {
    if (didAutoPromptRef.current) return;
    didAutoPromptRef.current = true;
    const state = useMapStore.getState();
    if (!state.locationPrompted && !state.locationConsentGranted) {
      state.setLocationPrompted(true);
      setConsentModalOpen(true);
    }
  }, []);

  // Viewport-based data fetching — fetchForCurrentView must be called
  // from the Map's onLoad to kick off the first fetch once the map is ready.
  const { fetchForCurrentView } = useMapData(mapRef);

  // On map load, find the first `place_*` symbol layer in the basemap style
  // so we can insert our station cluster/marker layers BEFORE it. That way
  // city/town labels from the basemap render above our station circles.
  const handleMapLoad = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (map) {
      const layers = map.getStyle()?.layers || [];
      // Carto uses `place_*` layer ids; Protomaps uses `places_*`. Accept both
      // so the beforeId insertion works against either basemap.
      const firstPlaceLabel = layers.find(
        (l) => l.type === "symbol"
            && typeof l.id === "string"
            && (l.id.startsWith("place_") || l.id.startsWith("places_"))
      );
      if (firstPlaceLabel) setPlaceLabelBeforeId(firstPlaceLabel.id);
    }
    fetchForCurrentView();
  }, [fetchForCurrentView]);

  /* ── Build GeoJSON from stations ───────────────── */
  const selectedSet = useMemo(
    () => new Set(selectedStations.map((s) => s.station_number)),
    [selectedStations]
  );

  // Filter out stations without data unless showNoData is enabled
  const visibleStations = useMemo(
    () => showNoData ? stations : stations.filter((s) => s.latest_reading != null),
    [stations, showNoData]
  );

  // Per-province cluster markers use the lightweight /provinces endpoint
  // (fetched once on mount) so counts reflect all stations in the province,
  // not just whatever happens to be loaded in the current viewport. Falls
  // back to empty until the counts request resolves.
  const provinceAggregateGeojson = useMemo(() => {
    if (!provinceCounts) return { type: "FeatureCollection", features: [] };
    const features = [];
    for (const p of provinceCounts) {
      if (provinceFilter && p.province_code !== provinceFilter) continue;
      const anchor = PROVINCE_LABEL_ANCHORS[p.province_code];
      if (!anchor) continue;

      let count;
      if (typeFilter === "R") {
        count = showNoData ? p.river_count : p.river_with_reading;
      } else if (typeFilter === "L") {
        count = showNoData ? p.lake_count : p.lake_with_reading;
      } else {
        count = showNoData
          ? p.river_count + p.lake_count
          : p.river_with_reading + p.lake_with_reading;
      }
      if (!count) continue;

      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: anchor },
        properties: {
          code: p.province_code,
          count,
          countLabel: count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count),
        },
      });
    }
    return { type: "FeatureCollection", features };
  }, [provinceCounts, provinceFilter, typeFilter, showNoData]);

  const geojson = useMemo(() => ({
    type: "FeatureCollection",
    features: visibleStations.map((station) => {
      const reading = station.latest_reading;
      const primaryRating =
        reading?.flow_rating || reading?.level_rating || "none";
      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [station.longitude, station.latitude],
        },
        properties: {
          stationNumber: station.station_number,
          stationName: station.station_name,
          stationType: station.station_type,
          primaryRating,
          isSelected: selectedSet.has(station.station_number),
        },
      };
    }),
  }), [visibleStations, selectedSet]);

  /* ── Selected station object for popup ─────────── */
  const popupStation = useMemo(
    () => visibleStations.find((s) => s.station_number === selectedStationNumber),
    [visibleStations, selectedStationNumber]
  );

  /* ── Click handlers ────────────────────────────── */
  const handleMapClick = useCallback(
    (event) => {
      const map = mapRef.current?.getMap();
      if (!map) return;

      // Check for cluster clicks first
      const clusterFeatures = map.queryRenderedFeatures(event.point, {
        layers: ["clusters"],
      });
      if (clusterFeatures.length > 0) {
        const cluster = clusterFeatures[0];
        const source = map.getSource("stations");
        const clusterId = cluster.properties.cluster_id;
        const center = cluster.geometry.coordinates;

        // MapLibre v3+ returns a Promise; older versions use a callback
        try {
          const result = source.getClusterExpansionZoom(clusterId);
          if (result && typeof result.then === "function") {
            result.then((zoom) => {
              map.easeTo({ center, zoom: zoom + 0.5 });
            });
          } else {
            // Callback style (shouldn't reach here with modern maplibre-gl)
            map.easeTo({ center, zoom: (result ?? map.getZoom()) + 2 });
          }
        } catch {
          // Fallback — just zoom in by 2 levels
          map.easeTo({ center, zoom: map.getZoom() + 2 });
        }
        return;
      }

      // Check for station marker clicks
      const markerFeatures = map.queryRenderedFeatures(event.point, {
        layers: ["station-markers"],
      });
      if (markerFeatures.length > 0) {
        const stationNumber = markerFeatures[0].properties.stationNumber;
        setSelectedStationNumber(stationNumber);
        return;
      }

      // Province overlay — only consulted at low zoom levels.
      // Zooms into the province's bounds but does NOT set the province
      // filter: border-area users often want to see stations in both
      // adjacent provinces, and they can still opt into a province
      // filter via the dropdown.
      if (map.getZoom() < PROVINCE_OVERLAY_MAX_ZOOM) {
        const provinceFeatures = map.queryRenderedFeatures(event.point, {
          layers: ["province-fills"],
        });
        if (provinceFeatures.length > 0) {
          const code = provinceFeatures[0].properties.code;
          const bounds = PROVINCE_BOUNDS[code];
          if (bounds) {
            map.fitBounds(
              [
                [bounds[0], bounds[1]],
                [bounds[2], bounds[3]],
              ],
              { padding: 40, duration: 800 }
            );
          }
          return;
        }
      }

      setSelectedStationNumber(null);
    },
    [setSelectedStationNumber]
  );

  /* ── Province hover feedback ──────────────────── */
  const handleMouseMove = useCallback((event) => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    const clearHover = () => {
      if (hoveredProvinceRef.current != null) {
        map.setFeatureState(
          { source: "provinces", id: hoveredProvinceRef.current },
          { hover: false }
        );
        hoveredProvinceRef.current = null;
      }
    };

    if (map.getZoom() >= PROVINCE_OVERLAY_MAX_ZOOM) {
      clearHover();
      return;
    }

    const features = map.queryRenderedFeatures(event.point, {
      layers: ["province-fills"],
    });
    const nextId = features.length > 0 ? features[0].id : null;
    if (nextId === hoveredProvinceRef.current) return;

    clearHover();
    if (nextId != null) {
      map.setFeatureState(
        { source: "provinces", id: nextId },
        { hover: true }
      );
      map.getCanvas().style.cursor = "pointer";
    } else {
      map.getCanvas().style.cursor = "";
    }
    hoveredProvinceRef.current = nextId;
  }, []);

  /* ── Cursor styling ────────────────────────────── */
  const handleMouseEnter = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = "pointer";
  }, []);

  const handleMouseLeave = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = "";
  }, []);

  const handleZoomIn = useCallback(() => {
    mapRef.current?.getMap()?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    mapRef.current?.getMap()?.zoomOut();
  }, []);

  const handleResetNorth = useCallback(() => {
    mapRef.current?.getMap()?.resetNorth();
  }, []);

  const requestGeolocation = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      showToast("Geolocation is not supported by your browser", "error");
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        // Clear the spinner first so it resets even if any of the downstream
        // calls (easeTo, showToast) throw for any reason.
        setIsLocating(false);
        const { latitude, longitude, accuracy } = position.coords;
        setUserLocation({ latitude, longitude, accuracy });
        mapRef.current?.getMap()?.easeTo({
          center: [longitude, latitude],
          zoom: 12,
          duration: 1200,
        });
        showToast("Location found", "success");
      },
      (error) => {
        setIsLocating(false);
        const messages = {
          1: "Location permission denied",
          2: "Your location is currently unavailable",
          3: "Timed out while requesting your location",
        };
        showToast(messages[error.code] || "Could not get your location", "error");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }, [setUserLocation, showToast]);

  const handleLocateMe = useCallback(() => {
    if (locationConsentGranted) {
      requestGeolocation();
    } else {
      setConsentModalOpen(true);
    }
  }, [locationConsentGranted, requestGeolocation]);

  const handleConsentConfirm = useCallback(() => {
    setLocationConsentGranted(true);
    setConsentModalOpen(false);
    requestGeolocation();
  }, [setLocationConsentGranted, requestGeolocation]);

  const userLocationGeojson = useMemo(() => {
    if (!userLocation) return null;
    return {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [userLocation.longitude, userLocation.latitude],
          },
          properties: {},
        },
      ],
    };
  }, [userLocation]);

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        {...viewState}
        onMove={(event) => setViewState(event.viewState)}
        onLoad={handleMapLoad}
        onClick={handleMapClick}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        interactiveLayerIds={["clusters", "station-markers", "province-fills"]}
        mapStyle={MAP_STYLE}
        maxZoom={15}
        style={{ width: "100%", height: "100%" }}
      >
        <Source
          id="provinces"
          type="geojson"
          data="/provinces.geojson"
          promoteId="code"
        >
          <Layer {...provinceFillLayer} />
          <Layer {...provinceBorderLayer} />
        </Source>

        <Source
          id="province-clusters"
          type="geojson"
          data={provinceAggregateGeojson}
        >
          <Layer {...provinceClusterCircleLayer} />
          <Layer {...provinceClusterCountLayer} />
        </Source>

        <Source
          id="province-label-anchors"
          type="geojson"
          data={PROVINCE_LABEL_GEOJSON}
        >
          <Layer {...provinceLabelLayer} />
        </Source>

        <Source
          id="stations"
          type="geojson"
          data={geojson}
          cluster={true}
          clusterMaxZoom={13}
          clusterRadius={50}
        >
          <Layer {...clusterLayer} beforeId={placeLabelBeforeId || undefined} />
          <Layer {...clusterCountLayer} beforeId={placeLabelBeforeId || undefined} />
          <Layer {...stationMarkerLayer} beforeId={placeLabelBeforeId || undefined} />
        </Source>

        {userLocationGeojson && (
          <Source id="user-location" type="geojson" data={userLocationGeojson}>
            <Layer
              id="user-location-pulse"
              type="circle"
              paint={{
                "circle-radius": 16,
                "circle-color": "#1e6ba8",
                "circle-opacity": 0.2,
                "circle-stroke-color": "#1e6ba8",
                "circle-stroke-width": 1,
                "circle-stroke-opacity": 0.4,
              }}
            />
            <Layer
              id="user-location-dot"
              type="circle"
              paint={{
                "circle-radius": 7,
                "circle-color": "#2196f3",
                "circle-stroke-color": "#ffffff",
                "circle-stroke-width": 3,
              }}
            />
          </Source>
        )}

        {popupStation && (
          <Popup
            longitude={popupStation.longitude}
            latitude={popupStation.latitude}
            anchor="bottom"
            onClose={() => setSelectedStationNumber(null)}
            closeOnClick={false}
            maxWidth="320px"
          >
            <MapStationCard station={popupStation} />
          </Popup>
        )}
      </Map>

      {/* Left column — filter panel + navigation controls */}
      <div className="absolute top-3 left-3 z-10 flex flex-col items-start gap-2">
        <MapFilterPanel mapRef={mapRef} />
        <div className="bg-white rounded-lg shadow-md border border-slate-200 flex flex-col overflow-hidden">
          <button
            onClick={handleZoomIn}
            className="px-2.5 py-2 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer text-lg leading-none font-medium"
            aria-label="Zoom in"
          >
            +
          </button>
          <div className="h-px bg-slate-200" />
          <button
            onClick={handleZoomOut}
            className="px-2.5 py-2 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer text-lg leading-none font-medium"
            aria-label="Zoom out"
          >
            &minus;
          </button>
          <div className="h-px bg-slate-200" />
          <button
            onClick={handleResetNorth}
            className="px-2.5 py-2 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer text-sm leading-none"
            aria-label="Reset north"
          >
            <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polygon points="12 2 15 10 12 8 9 10" fill="currentColor" stroke="none" />
              <line x1="12" y1="8" x2="12" y2="22" />
            </svg>
          </button>
          <div className="h-px bg-slate-200" />
          <button
            onClick={handleLocateMe}
            disabled={isLocating}
            className="px-2.5 py-2 text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer text-sm leading-none disabled:opacity-60 disabled:cursor-wait"
            aria-label={isLocating ? "Getting your location" : "Show my location"}
          >
            {isLocating ? (
              <svg className="w-4 h-4 mx-auto animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
                <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            ) : (
              <svg className="w-4 h-4 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <circle cx="12" cy="12" r="8" />
                <line x1="12" y1="2" x2="12" y2="5" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="2" y1="12" x2="5" y2="12" />
                <line x1="19" y1="12" x2="22" y2="12" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <LocationConsentModal
        isOpen={consentModalOpen}
        onConfirm={handleConsentConfirm}
        onCancel={() => setConsentModalOpen(false)}
      />
    </div>
  );
}
