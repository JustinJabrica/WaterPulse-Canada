/**
 * Pure aggregation helpers shared by the map's SelectionSummaryPanel and
 * the collection detail page. Computing the same stats (avg flow, dominant
 * rating, weather summary, etc.) over a list of stations + their cached
 * weather data, no React imports.
 *
 * Inputs throughout: `stations` is an array of station objects with the
 * following shape (a subset of StationWithReading from the backend):
 *   {
 *     station_number, station_name, station_type, latitude, longitude,
 *     latest_reading: { discharge, water_level, flow_rating, level_rating } | null,
 *   }
 *
 * Weather summary additionally takes `weatherCache`, a map keyed by
 * station_number whose values are `StationWeatherResponse` payloads from
 * GET /api/stations/{number}/weather.
 */

/** Find the most-frequent value in an array, ignoring falsy entries. */
export function mode(values) {
  const counts = {};
  values.forEach((v) => {
    if (v) counts[v] = (counts[v] || 0) + 1;
  });
  let best = null;
  let bestCount = 0;
  for (const [val, count] of Object.entries(counts)) {
    if (count > bestCount) {
      best = val;
      bestCount = count;
    }
  }
  return best;
}

/** Format a time string (HH:MM or ISO) to a short local display. */
export function formatTime(timeStr) {
  if (!timeStr) return null;
  try {
    const date = new Date(timeStr);
    if (isNaN(date.getTime())) return timeStr;
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return timeStr;
  }
}

/** Geographic midpoint of an array of stations. Returns null for empty input. */
export function midpoint(stations) {
  if (!stations || stations.length === 0) return null;
  const sum = stations.reduce(
    (acc, s) => ({ lat: acc.lat + s.latitude, lon: acc.lon + s.longitude }),
    { lat: 0, lon: 0 }
  );
  return { lat: sum.lat / stations.length, lon: sum.lon / stations.length };
}

/**
 * Bounding box for an array of stations, suitable for MapLibre fitBounds.
 * Returns null for empty input.
 */
export function stationsBounds(stations) {
  if (!stations || stations.length === 0) return null;
  const lats = stations.map((s) => s.latitude).filter(Number.isFinite);
  const lons = stations.map((s) => s.longitude).filter(Number.isFinite);
  if (lats.length === 0 || lons.length === 0) return null;
  return {
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats),
    minLon: Math.min(...lons),
    maxLon: Math.max(...lons),
  };
}

/**
 * Aggregate flow/level/rating across a list of stations. Lake/reservoir
 * stations (station_type === "L") are excluded from the level average
 * because their elevation values are on a different scale.
 */
export function computeReadingSummary(stations) {
  const withReading = (stations || []).filter((s) => s.latest_reading);

  const flows = withReading
    .filter((s) => s.latest_reading.discharge != null)
    .map((s) => ({ value: s.latest_reading.discharge, name: s.station_name }));

  const levels = withReading
    .filter((s) => s.station_type !== "L" && s.latest_reading.water_level != null)
    .map((s) => ({ value: s.latest_reading.water_level, name: s.station_name }));

  const flowRatings = withReading
    .map((s) => s.latest_reading.flow_rating)
    .filter(Boolean);
  const levelRatings = withReading
    .map((s) => s.latest_reading.level_rating)
    .filter(Boolean);

  const avgFlow = flows.length
    ? (flows.reduce((sum, f) => sum + f.value, 0) / flows.length).toFixed(1)
    : null;
  const avgLevel = levels.length
    ? (levels.reduce((sum, l) => sum + l.value, 0) / levels.length).toFixed(1)
    : null;

  const highFlow = flows.length
    ? flows.reduce((a, b) => (b.value > a.value ? b : a))
    : null;
  const lowFlow = flows.length
    ? flows.reduce((a, b) => (b.value < a.value ? b : a))
    : null;
  const highLevel = levels.length
    ? levels.reduce((a, b) => (b.value > a.value ? b : a))
    : null;
  const lowLevel = levels.length
    ? levels.reduce((a, b) => (b.value < a.value ? b : a))
    : null;

  return {
    avgFlow,
    avgLevel,
    highFlow: highFlow
      ? { value: highFlow.value.toFixed(1), name: highFlow.name }
      : null,
    lowFlow: lowFlow
      ? { value: lowFlow.value.toFixed(1), name: lowFlow.name }
      : null,
    highLevel: highLevel
      ? { value: highLevel.value.toFixed(1), name: highLevel.name }
      : null,
    lowLevel: lowLevel
      ? { value: lowLevel.value.toFixed(1), name: lowLevel.name }
      : null,
    dominantFlowRating: mode(flowRatings),
    dominantLevelRating: mode(levelRatings),
  };
}

/**
 * Aggregate weather (avg/high/low temp, earliest sunrise, latest sunset)
 * across a list of stations using a pre-fetched weatherCache. Stations
 * without a cached entry are silently skipped.
 */
export function computeWeatherSummary(stations, weatherCache) {
  const entries = (stations || [])
    .map((s) => ({ station: s, weather: weatherCache?.[s.station_number] }))
    .filter((e) => e.weather);

  const temps = entries
    .filter((e) => e.weather.weather?.current?.temperature_c != null)
    .map((e) => ({
      value: e.weather.weather.current.temperature_c,
      name: e.station.station_name,
    }));

  const sunrises = entries
    .filter((e) => e.weather.weather?.current?.sunrise)
    .map((e) => ({
      value: e.weather.weather.current.sunrise,
      name: e.station.station_name,
    }));

  const sunsets = entries
    .filter((e) => e.weather.weather?.current?.sunset)
    .map((e) => ({
      value: e.weather.weather.current.sunset,
      name: e.station.station_name,
    }));

  const avgTemp = temps.length
    ? (temps.reduce((sum, t) => sum + t.value, 0) / temps.length).toFixed(1)
    : null;

  const highTemp = temps.length
    ? temps.reduce((a, b) => (b.value > a.value ? b : a))
    : null;
  const lowTemp = temps.length
    ? temps.reduce((a, b) => (b.value < a.value ? b : a))
    : null;

  const earliestSunrise = sunrises.length
    ? sunrises.reduce((a, b) => (a.value < b.value ? a : b))
    : null;
  const latestSunset = sunsets.length
    ? sunsets.reduce((a, b) => (a.value > b.value ? a : b))
    : null;

  return {
    avgTemp,
    highTemp: highTemp
      ? { value: highTemp.value.toFixed(1), name: highTemp.name }
      : null,
    lowTemp: lowTemp
      ? { value: lowTemp.value.toFixed(1), name: lowTemp.name }
      : null,
    earliestSunrise,
    latestSunset,
    loadedCount: entries.length,
  };
}
