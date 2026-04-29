"use client";

import { useEffect, useRef, useState } from "react";

// Photon (komoot) is OSM-based like Nominatim but built for autocomplete:
// partial-word queries work, and OSM key/value tags come through reliably.
const PHOTON_URL = "https://photon.komoot.io/api/";
// Canada bounding box: west, south, east, north — restricts the search to
// places in Canada. Photon biases by bbox rather than enforcing it strictly,
// so we also drop non-Canada results client-side as a belt-and-braces guard.
const CANADA_BBOX = "-141.0,41.7,-52.6,83.1";
const DEBOUNCE_MS = 600;
const MIN_QUERY_LENGTH = 2;
const MAX_RESULTS = 6;

const SETTLEMENT_OSM_VALUES = {
  city: "City",
  town: "Town",
  village: "Village",
  hamlet: "Hamlet",
  suburb: "Suburb",
  neighbourhood: "Neighbourhood",
  quarter: "Quarter",
  locality: "Locality",
  isolated_dwelling: "Locality",
};
const RIVER_OSM_VALUES = { river: "River", stream: "Stream", canal: "Canal" };
const LAKE_OSM_VALUES = { water: "Lake", bay: "Bay", strait: "Strait" };

// Map a Photon GeoJSON Feature to our internal shape, or return null to drop it.
function shapeResult(feature) {
  const props = feature?.properties || {};
  const coords = feature?.geometry?.coordinates || [];
  const lon = coords[0];
  const lat = coords[1];
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  if (props.country && props.country !== "Canada") return null;

  const key = props.osm_key;
  const value = props.osm_value;
  let kind = null;
  let label = null;

  if (key === "place" && SETTLEMENT_OSM_VALUES[value]) {
    kind = "settlement";
    label = SETTLEMENT_OSM_VALUES[value];
  } else if (key === "waterway" && RIVER_OSM_VALUES[value]) {
    kind = "river";
    label = RIVER_OSM_VALUES[value];
  } else if (key === "natural" && LAKE_OSM_VALUES[value]) {
    kind = value === "bay" ? "bay" : value === "strait" ? "strait" : "lake";
    label = LAKE_OSM_VALUES[value];
  } else {
    return null;
  }

  const baseName = props.name || "Unknown";
  const region = [props.city, props.county, props.state]
    .filter(Boolean)
    .filter((part) => part !== baseName);
  const displayName = region.length > 0 ? `${baseName}, ${region.join(", ")}` : baseName;

  // Photon's extent is [minLon, maxLat, maxLon, minLat] — note the y-axis
  // ordering differs from Nominatim's boundingbox.
  let bbox = null;
  if (Array.isArray(props.extent) && props.extent.length === 4) {
    const [minLon, maxLat, maxLon, minLat] = props.extent.map(parseFloat);
    if ([minLat, maxLat, minLon, maxLon].every(Number.isFinite)) {
      bbox = { minLat, maxLat, minLon, maxLon };
    }
  }

  return {
    id: `${props.osm_type}-${props.osm_id}`,
    name: displayName,
    kind,
    label,
    lat,
    lon,
    bbox,
  };
}

function pickZoomForResult(result) {
  if (result.kind === "settlement") {
    if (result.label === "City" || result.label === "Town") return 11;
    return 13;
  }
  return 12;
}

// Tiny bboxes around point features produce awkward fitBounds animations;
// fall back to flyTo for those.
function bboxIsMeaningful(bbox) {
  if (!bbox) return false;
  const dLat = bbox.maxLat - bbox.minLat;
  const dLon = bbox.maxLon - bbox.minLon;
  return dLat > 0.005 || dLon > 0.005;
}

export default function MapSearchBar({ mapRef }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setResults([]);
      setStatus("idle");
      if (abortRef.current) abortRef.current.abort();
      return;
    }

    const handle = setTimeout(async () => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const params = new URLSearchParams({
        q: trimmed,
        limit: "20",
        lang: "en",
        bbox: CANADA_BBOX,
      });

      setStatus("loading");
      try {
        const response = await fetch(`${PHOTON_URL}?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Photon ${response.status}`);
        const data = await response.json();
        const features = Array.isArray(data?.features) ? data.features : [];
        const shaped = features
          .map(shapeResult)
          .filter(Boolean)
          .slice(0, MAX_RESULTS);
        setResults(shaped);
        setStatus("idle");
        setOpen(true);
        setActiveIndex(-1);
      } catch (error) {
        if (error.name === "AbortError") return;
        setStatus("error");
        setResults([]);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const flyToResult = (result) => {
    const map = mapRef?.current?.getMap?.();
    if (!map) return;

    if (bboxIsMeaningful(result.bbox)) {
      map.fitBounds(
        [
          [result.bbox.minLon, result.bbox.minLat],
          [result.bbox.maxLon, result.bbox.maxLat],
        ],
        { padding: 60, maxZoom: 13, duration: 1000 }
      );
    } else {
      map.flyTo({
        center: [result.lon, result.lat],
        zoom: pickZoomForResult(result),
        duration: 1000,
      });
    }
  };

  const handleSelect = (result) => {
    flyToResult(result);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event) => {
    if (event.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
      return;
    }
    if (!open || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => (i + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => (i <= 0 ? results.length - 1 : i - 1));
    } else if (event.key === "Enter") {
      const pick = activeIndex >= 0 ? results[activeIndex] : results[0];
      if (pick) {
        event.preventDefault();
        handleSelect(pick);
      }
    }
  };

  const showDropdown =
    open &&
    query.trim().length >= MIN_QUERY_LENGTH &&
    status !== "loading";

  return (
    <div ref={containerRef} className="relative w-64">
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search cities, rivers, lakes"
          className="w-full pl-8 pr-8 py-2 rounded-lg bg-white shadow-md border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#2196f3]/30 focus:border-[#2196f3]/50 transition-all"
          aria-label="Search for a city, river, or lake"
        />
        {status === "loading" && (
          <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400">
            <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
              <path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
        )}
        {status !== "loading" && query.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setResults([]);
              setOpen(false);
              setActiveIndex(-1);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            aria-label="Clear search"
          >
            <svg
              className="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      {showDropdown && (
        <ul
          role="listbox"
          className="absolute left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-slate-200 overflow-hidden z-20 max-h-80 overflow-y-auto"
        >
          {status === "error" && (
            <li className="px-3 py-2 text-xs text-red-500">
              Search is unavailable right now
            </li>
          )}
          {status !== "error" && results.length === 0 && (
            <li className="px-3 py-2 text-xs text-slate-500">No matches</li>
          )}
          {results.map((result, i) => (
            <li key={result.id} role="option" aria-selected={i === activeIndex}>
              <button
                type="button"
                onMouseEnter={() => setActiveIndex(i)}
                onClick={() => handleSelect(result)}
                className={`w-full text-left px-3 py-2 text-sm flex items-start gap-2 cursor-pointer transition-colors ${
                  i === activeIndex ? "bg-slate-100" : "hover:bg-slate-50"
                }`}
              >
                <span className="flex-1 min-w-0 text-slate-900 line-clamp-2 break-words">
                  {result.name}
                </span>
                <span className="shrink-0 text-[10px] uppercase tracking-wide text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                  {result.label}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
