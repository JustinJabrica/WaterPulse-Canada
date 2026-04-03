"""
Weather service.

Fetches current weather conditions and daily forecast from the Open-Meteo API
for station locations. Supports batch requests to minimize API calls.

The backend sends raw numerical values. The frontend is responsible for
interpreting these into user-friendly categories and descriptions
(e.g., converting visibility_m into "Foggy" / "Clear" / "Very Clear").

Open-Meteo free tier: no API key needed, limit ~10,000 calls/day.

Variables are chosen specifically for river/reservoir visitors:
- Temperature + feels-like: personal comfort and safety
- Precipitation + weather code: rain vs drizzle vs snow, intensity
- Precipitation probability: trip planning
- Visibility: navigation and safety on water
- Wind speed + gusts: canoe/kayak/boat safety
- UV index: sun exposure on open water
- Sunrise/sunset: daylight planning
- Weather code: covers thunderstorms (critical safety on water)
"""

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Current weather variables
CURRENT_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "visibility",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "uv_index",
    "is_day",
]

# Daily forecast variables
DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "sunrise",
    "sunset",
    "uv_index_max",
    "visibility_mean",
]

# Air quality variables (current hourly values)
AIR_QUALITY_VARIABLES = [
    "us_aqi",
    "pm10",
    "pm2_5",
]

# WMO weather interpretation codes
# Sent alongside raw codes so the frontend has a reference,
# but the frontend can also implement its own descriptions
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
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
}


def build_current_weather(current_data: dict, daily_data: dict | None = None) -> dict:
    """Build a current weather dict, including today's sunrise/sunset."""
    weather_code = current_data.get("weather_code")

    # Extract today's sunrise and sunset from the daily data (first entry = today)
    sunrise = None
    sunset = None
    if daily_data and "sunrise" in daily_data and daily_data["sunrise"]:
        sunrise = daily_data["sunrise"][0]
    if daily_data and "sunset" in daily_data and daily_data["sunset"]:
        sunset = daily_data["sunset"][0]

    return {
        "temperature_c": current_data.get("temperature_2m"),
        "apparent_temperature_c": current_data.get("apparent_temperature"),
        "humidity_pct": current_data.get("relative_humidity_2m"),
        "precipitation_mm": current_data.get("precipitation"),
        "weather_code": weather_code,
        "weather_description": WMO_CODES.get(weather_code, "Unknown"),
        "visibility_m": current_data.get("visibility"),
        "wind_speed_kmh": current_data.get("wind_speed_10m"),
        "wind_gusts_kmh": current_data.get("wind_gusts_10m"),
        "wind_direction_deg": current_data.get("wind_direction_10m"),
        "uv_index": current_data.get("uv_index"),
        "is_day": bool(current_data.get("is_day")),
        "sunrise": sunrise,
        "sunset": sunset,
        "time": current_data.get("time"),
    }


def build_daily_forecast(daily_data: dict) -> list[dict]:
    """Build a list of daily forecast dicts from Open-Meteo response data."""
    if not daily_data or "time" not in daily_data:
        return []

    days = []
    for i, date_str in enumerate(daily_data["time"]):
        weather_code = daily_data.get("weather_code", [None])[i]
        days.append({
            "date": date_str,
            "weather_code": weather_code,
            "weather_description": WMO_CODES.get(weather_code, "Unknown"),
            "temperature_max_c": daily_data.get("temperature_2m_max", [None])[i],
            "temperature_min_c": daily_data.get("temperature_2m_min", [None])[i],
            "apparent_temperature_max_c": daily_data.get(
                "apparent_temperature_max", [None]
            )[i],
            "apparent_temperature_min_c": daily_data.get(
                "apparent_temperature_min", [None]
            )[i],
            "precipitation_sum_mm": daily_data.get("precipitation_sum", [None])[i],
            "precipitation_probability_pct": daily_data.get(
                "precipitation_probability_max", [None]
            )[i],
            "wind_speed_max_kmh": daily_data.get("wind_speed_10m_max", [None])[i],
            "wind_gusts_max_kmh": daily_data.get("wind_gusts_10m_max", [None])[i],
            "sunrise": daily_data.get("sunrise", [None])[i],
            "sunset": daily_data.get("sunset", [None])[i],
            "uv_index_max": daily_data.get("uv_index_max", [None])[i],
            "visibility_mean_m": daily_data.get("visibility_mean", [None])[i],
        })
    return days


async def fetch_weather_batch(
    client: httpx.AsyncClient,
    latitudes: list[float],
    longitudes: list[float],
) -> list[dict | None]:
    """
    Fetch weather for a batch of coordinates from Open-Meteo.
    Returns a list of weather dicts (one per coordinate), or None for failures.
    Retries with exponential backoff on 429 rate-limit responses.
    """
    params = {
        "latitude": ",".join(str(lat) for lat in latitudes),
        "longitude": ",".join(str(lon) for lon in longitudes),
        "current": ",".join(CURRENT_VARIABLES),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "America/Edmonton",
        "forecast_days": 7,
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }

    for attempt in range(settings.WEATHER_MAX_RETRIES + 1):
        try:
            response = await client.get(settings.OPEN_METEO_FORECAST_URL, params=params, timeout=30)
            if response.status_code == 429:
                if attempt < settings.WEATHER_MAX_RETRIES:
                    wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                    logger.warning(f"Open-Meteo forecast 429 rate-limited, retrying in {wait}s (attempt {attempt + 1}/{settings.WEATHER_MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.error(f"Open-Meteo forecast 429 after {settings.WEATHER_MAX_RETRIES} retries, skipping batch")
                    return [None] * len(latitudes)
            response.raise_for_status()
            data = response.json()
            break
        except httpx.TimeoutException:
            if attempt < settings.WEATHER_MAX_RETRIES:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Open-Meteo forecast timeout, retrying in {wait}s (attempt {attempt + 1}/{settings.WEATHER_MAX_RETRIES})")
                await asyncio.sleep(wait)
                continue
            logger.error("Open-Meteo forecast timeout after all retries")
            return [None] * len(latitudes)
        except httpx.HTTPError as e:
            logger.error(f"Open-Meteo batch request failed: {e}")
            return [None] * len(latitudes)

    # Single location returns a dict, multiple returns a list
    if isinstance(data, dict) and "current" in data:
        results = [data]
    elif isinstance(data, list):
        results = data
    else:
        logger.warning("Unexpected Open-Meteo response format")
        return [None] * len(latitudes)

    weather_list = []
    for item in results:
        if item and "current" in item:
            daily_data = item.get("daily", {})
            current = build_current_weather(item["current"], daily_data)
            daily = build_daily_forecast(daily_data)
            weather_list.append({
                "current": current,
                "daily_forecast": daily,
                "elevation_m": item.get("elevation"),
            })
        else:
            weather_list.append(None)

    return weather_list


async def fetch_air_quality_batch(
    client: httpx.AsyncClient,
    latitudes: list[float],
    longitudes: list[float],
) -> list[dict | None]:
    """
    Fetch current air quality for a batch of coordinates from Open-Meteo.
    Returns a list of air quality dicts (one per coordinate), or None for failures.
    """
    params = {
        "latitude": ",".join(str(lat) for lat in latitudes),
        "longitude": ",".join(str(lon) for lon in longitudes),
        "current": ",".join(AIR_QUALITY_VARIABLES),
        "timezone": "America/Edmonton",
    }

    for attempt in range(settings.WEATHER_MAX_RETRIES + 1):
        try:
            response = await client.get(settings.OPEN_METEO_AQI_URL, params=params, timeout=30)
            if response.status_code == 429:
                if attempt < settings.WEATHER_MAX_RETRIES:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Open-Meteo AQI 429 rate-limited, retrying in {wait}s (attempt {attempt + 1}/{settings.WEATHER_MAX_RETRIES})")
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.error(f"Open-Meteo AQI 429 after {settings.WEATHER_MAX_RETRIES} retries, skipping batch")
                    return [None] * len(latitudes)
            response.raise_for_status()
            data = response.json()
            break
        except httpx.TimeoutException:
            if attempt < settings.WEATHER_MAX_RETRIES:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Open-Meteo AQI timeout, retrying in {wait}s (attempt {attempt + 1}/{settings.WEATHER_MAX_RETRIES})")
                await asyncio.sleep(wait)
                continue
            logger.error("Open-Meteo AQI timeout after all retries")
            return [None] * len(latitudes)
        except httpx.HTTPError as e:
            logger.error(f"Open-Meteo air quality batch request failed: {e}")
            return [None] * len(latitudes)

    # Single location returns a dict, multiple returns a list
    if isinstance(data, dict) and "current" in data:
        results = [data]
    elif isinstance(data, list):
        results = data
    else:
        logger.warning("Unexpected Open-Meteo air quality response format")
        return [None] * len(latitudes)

    aq_list = []
    for item in results:
        if item and "current" in item:
            current = item["current"]
            aq_list.append({
                "us_aqi": current.get("us_aqi"),
                "pm2_5": current.get("pm2_5"),
                "pm10": current.get("pm10"),
                "time": current.get("time"),
            })
        else:
            aq_list.append(None)

    return aq_list


async def fetch_weather_for_stations(
    stations: list[dict],
) -> dict[str, dict]:
    """
    Fetch weather and air quality for all stations, batching requests.

    Args:
        stations: list of dicts with station_number, latitude, longitude

    Returns:
        dict mapping station_number -> weather data (including air quality)
    """
    valid_stations = [
        s for s in stations
        if s.get("latitude") and s.get("longitude")
    ]

    if not valid_stations:
        return {}

    logger.info(
        f"Fetching weather and air quality for {len(valid_stations)} stations "
        f"in {(len(valid_stations) + settings.WEATHER_BATCH_SIZE - 1) // settings.WEATHER_BATCH_SIZE} batches..."
    )

    weather_map = {}

    async with httpx.AsyncClient() as client:
        for i in range(0, len(valid_stations), settings.WEATHER_BATCH_SIZE):
            batch = valid_stations[i:i + settings.WEATHER_BATCH_SIZE]
            latitudes = [float(s["latitude"]) for s in batch]
            longitudes = [float(s["longitude"]) for s in batch]

            # Fetch weather and air quality concurrently for each batch
            weather_results, aq_results = await asyncio.gather(
                fetch_weather_batch(client, latitudes, longitudes),
                fetch_air_quality_batch(client, latitudes, longitudes),
            )

            for station, weather, aq in zip(batch, weather_results, aq_results):
                if weather:
                    if aq:
                        weather["air_quality"] = aq
                    weather_map[station["station_number"]] = weather

            # Delay between batches to avoid Open-Meteo rate limits
            if i + settings.WEATHER_BATCH_SIZE < len(valid_stations):
                await asyncio.sleep(settings.WEATHER_BATCH_DELAY)

    logger.info(
        f"Weather fetched for {len(weather_map)}/{len(valid_stations)} stations"
    )
    return weather_map


async def fetch_weather_for_single_station(
    latitude: float,
    longitude: float,
) -> dict | None:
    """
    Fetch weather + air quality for a single station coordinate.
    Returns a weather dict with {current, daily_forecast, air_quality, elevation_m}
    or None on failure.
    """
    async with httpx.AsyncClient() as client:
        weather_results, aq_results = await asyncio.gather(
            fetch_weather_batch(client, [latitude], [longitude]),
            fetch_air_quality_batch(client, [latitude], [longitude]),
        )

    weather = weather_results[0] if weather_results else None
    aq = aq_results[0] if aq_results else None

    if weather and aq:
        weather["air_quality"] = aq

    return weather
