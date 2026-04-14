import { useRef, useCallback, useMemo } from "react";
import Map, { Source, Layer, Popup } from "react-map-gl/maplibre";
import useMapStore from "@/stores/mapStore";
import useMapData from "./useMapData";
import MapStationCard from "@/components/MapStationCard";
import MapFilterPanel from "./MapFilterPanel";

/* ── Marker colour mapping ───────────────────────────
   Matches RATING_CONFIG from constants.js:
   Very Low = red, Low = amber, Average = emerald,
   High = blue, Very High = purple, No data = slate */
const RATING_COLOURS = {
  "very low": "#ef4444",
  low: "#f59e0b",
  average: "#10b981",
  high: "#3b82f6",
  "very high": "#a855f7",
  none: "#94a3b8",
};

const TILE_STYLE =
  "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json";

/* ── MapLibre layer definitions ──────────────────────
   Three layers render on top of a single GeoJSON source:
   1. Cluster circles — brand blue circles sized by point count
   2. Cluster labels — white count text inside cluster circles
   3. Station markers — individual coloured dots by rating */

const clusterLayer = {
  id: "clusters",
  type: "circle",
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
  filter: ["has", "point_count"],
  layout: {
    "text-field": "{point_count_abbreviated}",
    "text-size": 13,
    "text-font": ["Open Sans Bold"],
  },
  paint: {
    "text-color": "#ffffff",
  },
};

const stationMarkerLayer = {
  id: "station-markers",
  type: "circle",
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

  const viewState = useMapStore((s) => s.viewState);
  const setViewState = useMapStore((s) => s.setViewState);
  const selectedStationNumber = useMapStore((s) => s.selectedStationNumber);
  const setSelectedStationNumber = useMapStore((s) => s.setSelectedStationNumber);
  const stations = useMapStore((s) => s.stations);
  const selectedStations = useMapStore((s) => s.selectedStations);
  const showNoData = useMapStore((s) => s.showNoData);

  // Viewport-based data fetching — fetchForCurrentView must be called
  // from the Map's onLoad to kick off the first fetch once the map is ready.
  const { fetchForCurrentView } = useMapData(mapRef);

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
      } else {
        setSelectedStationNumber(null);
      }
    },
    [setSelectedStationNumber]
  );

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

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        {...viewState}
        onMove={(event) => setViewState(event.viewState)}
        onLoad={fetchForCurrentView}
        onClick={handleMapClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        interactiveLayerIds={["clusters", "station-markers"]}
        mapStyle={TILE_STYLE}
        style={{ width: "100%", height: "100%" }}
      >
        <Source
          id="stations"
          type="geojson"
          data={geojson}
          cluster={true}
          clusterMaxZoom={14}
          clusterRadius={50}
        >
          <Layer {...clusterLayer} />
          <Layer {...clusterCountLayer} />
          <Layer {...stationMarkerLayer} />
        </Source>

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
        <MapFilterPanel />
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
        </div>
      </div>
    </div>
  );
}
