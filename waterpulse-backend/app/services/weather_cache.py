"""
Weather cache service.

Serves cached weather from the station_weather table if fresh,
otherwise fetches from Open-Meteo for a single station and caches it.
"""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.station import Station
from app.models.weather import StationWeather
from app.services.weather import fetch_weather_for_single_station

logger = logging.getLogger(__name__)


async def get_station_weather(
    db: AsyncSession,
    station_number: str,
) -> dict | None:
    """
    Return weather for a station. Serves from cache if fresh
    (< WEATHER_CACHE_TTL_MINUTES old), otherwise fetches live
    from Open-Meteo, caches it, and returns.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(minutes=settings.WEATHER_CACHE_TTL_MINUTES)

    # Check cache
    result = await db.execute(
        select(StationWeather).where(
            StationWeather.station_number == station_number
        )
    )
    cached = result.scalar_one_or_none()

    if cached and cached.weather_fetched_at and cached.weather_fetched_at > cutoff:
        logger.debug(f"Weather cache hit for {station_number}")
        return cached.weather_data

    # Cache miss or stale — look up coordinates
    result = await db.execute(
        select(Station.latitude, Station.longitude).where(
            Station.station_number == station_number
        )
    )
    row = result.one_or_none()
    if not row or not row.latitude or not row.longitude:
        logger.warning(f"No coordinates for station {station_number}, cannot fetch weather")
        return None

    # Fetch from Open-Meteo
    logger.info(f"Fetching weather for {station_number} ({row.latitude}, {row.longitude})")
    weather_data = await fetch_weather_for_single_station(row.latitude, row.longitude)

    if weather_data is None:
        # Return stale cache if available, otherwise None
        if cached and cached.weather_data:
            logger.info(f"Open-Meteo failed for {station_number}, returning stale cache")
            return cached.weather_data
        return None

    # Upsert into cache
    stmt = pg_insert(StationWeather).values(
        station_number=station_number,
        weather_data=weather_data,
        weather_fetched_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["station_number"],
        set_={
            "weather_data": stmt.excluded.weather_data,
            "weather_fetched_at": stmt.excluded.weather_fetched_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

    return weather_data
