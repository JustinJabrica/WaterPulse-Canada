// ── Province names and codes ────────────────────────────────────────

export const PROVINCES = {
  AB: "Alberta",
  BC: "British Columbia",
  SK: "Saskatchewan",
  MB: "Manitoba",
  ON: "Ontario",
  QC: "Quebec",
  NB: "New Brunswick",
  NS: "Nova Scotia",
  PE: "Prince Edward Island",
  NL: "Newfoundland and Labrador",
  YT: "Yukon",
  NT: "Northwest Territories",
  NU: "Nunavut",
};

// ── Province bounding boxes (used to fly the map to a clicked province) ──
// Derived from public/provinces.geojson; format: [minLng, minLat, maxLng, maxLat].

export const PROVINCE_BOUNDS = {
  AB: [-120.001, 49, -110.001, 59.995],
  BC: [-138.939, 48.301, -114.035, 60.004],
  MB: [-102.002, 49, -89.18, 60],
  NB: [-69.04, 45.056, -63.776, 48.073],
  NL: [-67.782, 46.613, -52.62, 60.485],
  NS: [-66.9, 43.464, -59.81, 47.033],
  NT: [-136.446, 59.989, -101.984, 78.754],
  NU: [-120.665, 51.914, -61.079, 83.108],
  ON: [-95.154, 41.913, -74.325, 56.869],
  PE: [-64.417, 45.948, -61.971, 47.062],
  QC: [-80.11, 44.991, -57.101, 62.592],
  SK: [-110.001, 49, -101.367, 60],
  YT: [-141.003, 59.995, -123.817, 69.648],
};

// ── Province label anchor points ──────────────────────────────────
// One [lng, lat] per province at a visual mid-mass point on land, so the
// label layer can render one label per province instead of one per polygon ring.

export const PROVINCE_LABEL_ANCHORS = {
  AB: [-115.0, 54.5],
  BC: [-124.5, 54.0],
  SK: [-106.0, 54.0],
  MB: [-97.0, 54.5],
  ON: [-85.5, 50.0],
  QC: [-72.0, 52.0],
  NB: [-66.5, 46.6],
  NS: [-63.5, 45.2],
  PE: [-63.2, 46.4],
  NL: [-60.0, 53.5],
  YT: [-135.5, 63.5],
  NT: [-120.0, 65.0],
  NU: [-90.0, 67.0],
};

// ── Province fill colours for the map overlay ─────────────────────

export const PROVINCE_COLOURS = {
  BC: "#6B2D5B",
  AB: "#053293",
  SK: "#4B8C1B",
  MB: "#CD0001",
  ON: "#8B1A2B",
  QC: "#2B5BAE",
  NB: "#D4A017",
  NS: "#7BA3D4",
  PE: "#00968C",
  NL: "#C85A4A",
  YT: "#1B5E20",
  NT: "#5A8C7A",
  NU: "#E8A82E",
};

// ── Alberta basin names (used for basin-grouped views) ──────────────

export const BASIN_NAMES = {
  ATH_7: "Athabasca",
  BEA_7: "Beaver",
  BOW: "Bow",
  COL_6: "Columbia",
  FRA_6: "Fraser",
  HAY_7: "Hay",
  MIL_7: "Milk",
  NSA_7: "North Saskatchewan",
  OLD: "Oldman",
  PEA_7: "Peace",
  RED: "Red Deer",
  SSA: "South Saskatchewan",
};

// ── Rating pill colours ─────────────────────────────────────────────

export const RATING_CONFIG = {
  "very low":  { label: "Very Low",  color: "bg-red-100 text-red-800 border-red-200",         dot: "bg-red-500" },
  "low":       { label: "Low",       color: "bg-amber-100 text-amber-800 border-amber-200",   dot: "bg-amber-500" },
  "average":   { label: "Average",   color: "bg-emerald-100 text-emerald-800 border-emerald-200", dot: "bg-emerald-500" },
  "high":      { label: "High",      color: "bg-blue-100 text-blue-800 border-blue-200",      dot: "bg-blue-500" },
  "very high": { label: "Very High", color: "bg-purple-100 text-purple-800 border-purple-200", dot: "bg-purple-500" },
};

// ── WMO weather code descriptions ───────────────────────────────────

export const WMO_DESCRIPTIONS = {
  0: "Clear sky",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Foggy",
  48: "Depositing rime fog",
  51: "Light drizzle",
  53: "Moderate drizzle",
  55: "Dense drizzle",
  56: "Light freezing drizzle",
  57: "Dense freezing drizzle",
  61: "Slight rain",
  63: "Moderate rain",
  65: "Heavy rain",
  66: "Light freezing rain",
  67: "Heavy freezing rain",
  71: "Slight snow",
  73: "Moderate snow",
  75: "Heavy snow",
  77: "Snow grains",
  80: "Slight rain showers",
  81: "Moderate rain showers",
  82: "Violent rain showers",
  85: "Slight snow showers",
  86: "Heavy snow showers",
  95: "Thunderstorm",
  96: "Thunderstorm with slight hail",
  99: "Thunderstorm with heavy hail",
};

// ── AQI category labels ─────────────────────────────────────────────

export function getAqiCategory(aqi) {
  if (aqi == null) return null;
  if (aqi <= 50) return { label: "Good", color: "text-emerald-700" };
  if (aqi <= 100) return { label: "Moderate", color: "text-amber-700" };
  if (aqi <= 150) return { label: "Sensitive", color: "text-orange-700" };
  if (aqi <= 200) return { label: "Unhealthy", color: "text-red-700" };
  if (aqi <= 300) return { label: "Very Unhealthy", color: "text-purple-700" };
  return { label: "Hazardous", color: "text-rose-900" };
}

// ── Beaufort Wind Scale (km/h thresholds from Environment Canada) ───

const BEAUFORT_SCALE = [
  { force: 0,  maxKmh: 1,   label: "Calm" },
  { force: 1,  maxKmh: 5,   label: "Light Air" },
  { force: 2,  maxKmh: 11,  label: "Light Breeze" },
  { force: 3,  maxKmh: 19,  label: "Gentle Breeze" },
  { force: 4,  maxKmh: 28,  label: "Moderate Breeze" },
  { force: 5,  maxKmh: 38,  label: "Fresh Breeze" },
  { force: 6,  maxKmh: 49,  label: "Strong Breeze" },
  { force: 7,  maxKmh: 61,  label: "Near Gale" },
  { force: 8,  maxKmh: 74,  label: "Gale" },
  { force: 9,  maxKmh: 88,  label: "Strong Gale" },
  { force: 10, maxKmh: 102, label: "Storm" },
  { force: 11, maxKmh: 117, label: "Violent Storm" },
  { force: 12, maxKmh: Infinity, label: "Hurricane Force" },
];

export function getBeaufortScale(windSpeedKmh) {
  if (windSpeedKmh == null) return null;
  const entry = BEAUFORT_SCALE.find((b) => windSpeedKmh <= b.maxKmh);
  return entry || BEAUFORT_SCALE[BEAUFORT_SCALE.length - 1];
}

// ── Station type labels ─────────────────────────────────────────────

// Only water station types — meteorological stations are excluded from
// the dashboard and all readings endpoints (backend filters to R and L).
export const STATION_TYPES = {
  R: "River",
  L: "Lake / Reservoir",
};

/**
 * Human-readable names for data_source values from the backend.
 * Each provider registers its code here. Add new provincial providers
 * as they are built (e.g., bc: "BC Water Tool", sk: "WSA Saskatchewan").
 */
export const DATA_SOURCES = {
  alberta: "Rivers Alberta",
  eccc: "ECCC",
};
