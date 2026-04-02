"""
Current readings orchestrator.

Loops all registered providers, deduplicates readings with provincial
priority (Alberta runs first and wins for shared stations), computes
flow/level ratings against historical percentiles, and upserts into
the current_readings table. Weather is fetched separately on demand.

Provider order is defined in providers/__init__.py:
    [AlbertaProvider(), ECCCProvider()]
Alberta is first, so for the 374 shared stations, Alberta's reading
(which includes precipitation context) is always kept.

Supports selective refresh: pass station_numbers or province to only
update a subset of readings. Existing readings for other stations
are preserved (upsert, not delete-all).

Run frequency: On demand via the frontend or admin endpoints.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.models.station import Station
from app.models.reading import CurrentReading
from app.models.historical import HistoricalDailyMean
from app.services.providers import get_active_providers
from app.services.providers.base_provider import NormalizedReading

logger = logging.getLogger(__name__)

PERCENTILE_WINDOW_DAYS = 7
MIN_HISTORICAL_VALUES = 5


# ──────────────────────────────────────────────────────────────────────
# Percentile computation
# ──────────────────────────────────────────────────────────────────────


def compute_percentiles(values: list[float]) -> dict | None:
    """Compute percentiles from a list of historical values."""
    if len(values) < MIN_HISTORICAL_VALUES:
        return None

    values.sort()

    # Linear interpolation for a given percentile p (0-100).
    # Given a sorted list of values, finds the value at the requested
    # percentile by blending between the two nearest data points.
    def pct(vals, p):
        k = (p / 100) * (len(vals) - 1)  # k = exact position in the sorted list (fractional index)
        f = int(k)                         # f = the data point just below that position (floor)
        c = f + 1                          # c = the data point just above that position (ceiling)
        if c >= len(vals):
            return vals[-1]
        # Blend between the floor and ceiling values based on how far k falls between them
        return vals[f] + (k - f) * (vals[c] - vals[f])

    return {
        "p10": round(pct(values, 10), 4),
        "p25": round(pct(values, 25), 4),
        "p50": round(pct(values, 50), 4),
        "p75": round(pct(values, 75), 4),
        "p90": round(pct(values, 90), 4),
        "sample_size": len(values),
    }


def rate_value(value: float | None, percentiles: dict | None) -> str | None:
    """Rate a value against percentile thresholds."""
    if value is None or percentiles is None:
        return None
    if value < percentiles["p10"]:
        return "very low"
    elif value < percentiles["p25"]:
        return "low"
    elif value <= percentiles["p75"]:
        return "average"
    elif value <= percentiles["p90"]:
        return "high"
    else:
        return "very high"


def rate_pct_full(pct_full: float | None) -> str | None:
    """Rate reservoir fullness on a fixed scale."""
    if pct_full is None:
        return None
    if pct_full < 20:
        return "very low"
    elif pct_full < 40:
        return "low"
    elif pct_full <= 70:
        return "average"
    elif pct_full <= 90:
        return "high"
    else:
        return "very high"


def get_window_dates(target_date: datetime) -> list[str]:
    """Generate MM-DD strings for a +/- PERCENTILE_WINDOW_DAYS window."""
    return [
        (target_date + timedelta(days=offset)).strftime("%m-%d")
        for offset in range(-PERCENTILE_WINDOW_DAYS, PERCENTILE_WINDOW_DAYS + 1)
    ]


async def get_percentiles_for_station(
    db: AsyncSession,
    station_number: str,
    data_key: str,
    target_date: datetime,
) -> dict | None:
    """Query historical daily means within the window and compute percentiles."""
    window_dates = get_window_dates(target_date)

    result = await db.execute(
        select(HistoricalDailyMean.value).where(
            HistoricalDailyMean.station_number == station_number,
            HistoricalDailyMean.data_key == data_key,
            HistoricalDailyMean.month_day.in_(window_dates),
        )
    )
    values = [row[0] for row in result.all()]
    return compute_percentiles(values)


# ──────────────────────────────────────────────────────────────────────
# Merge readings — provincial providers take priority
# ──────────────────────────────────────────────────────────────────────


def _merge_readings(
    all_provider_readings: list[tuple[str, list[NormalizedReading]]],
) -> dict[str, NormalizedReading]:
    """
    Merge readings from all providers. Provincial providers (Alberta)
    are registered first in the provider list, so they run first and
    their readings are kept for shared stations. ECCC readings only
    fill in stations that the provincial providers don't cover.
    """
    merged: dict[str, NormalizedReading] = {}

    for _provider_name, readings in all_provider_readings:
        for reading in readings:
            if reading.station_number not in merged:
                merged[reading.station_number] = reading

    return merged


# ──────────────────────────────────────────────────────────────────────
# Main refresh function
# ──────────────────────────────────────────────────────────────────────


async def refresh_current_readings(
    db: AsyncSession,
    station_numbers: list[str] | None = None,
    province: str | None = None,
) -> dict:
    """
    Fetch current readings from all providers, deduplicate (provincial
    providers win for shared stations), compute ratings, and upsert
    into the current_readings table.

    Filters (passed through to providers):
        station_numbers — refresh only these specific stations
        province — refresh only stations in this province
    When both are None, refreshes all stations.
    """
    total_start = time.monotonic()
    scope = (
        f"stations {','.join(station_numbers[:5])}{'...' if station_numbers and len(station_numbers) > 5 else ''}"
        if station_numbers
        else f"province {province.upper()}" if province
        else "all stations"
    )
    logger.info(f"Starting readings refresh for {scope}...")

    # ── Phase 1: Fetch from all providers ──────────────────────────
    logger.info("[1/3] Fetching readings from providers...")
    fetch_start = time.monotonic()

    all_provider_readings: list[tuple[str, list[NormalizedReading]]] = []
    providers = get_active_providers()

    for provider in providers:
        try:
            readings = await provider.fetch_latest_readings(
                station_numbers=station_numbers,
                province=province,
            )
            all_provider_readings.append((provider.name, readings))
            logger.info(f"  {provider.name}: {len(readings)} readings fetched")
        except Exception as e:
            logger.error(f"  {provider.name}: fetch failed: {e}", exc_info=True)

    fetch_elapsed = time.monotonic() - fetch_start
    logger.info(f"[1/3] Fetch complete in {fetch_elapsed:.1f}s")

    # ── Phase 2: Merge and prepare station data ────────────────────
    logger.info("[2/3] Merging readings and preparing station data...")
    merge_start = time.monotonic()

    merged = _merge_readings(all_provider_readings)
    logger.info(f"  Merged into {len(merged)} unique station readings")

    if not merged:
        total_elapsed = time.monotonic() - total_start
        return {
            "readings_stored": 0,
            "stations_auto_created": 0,
            "elapsed_seconds": round(total_elapsed, 1),
            "timing": {
                "fetch_seconds": round(fetch_elapsed, 1),
            },
            "providers": {
                name: len(readings)
                for name, readings in all_provider_readings
            },
        }

    # Build station lookup for has_capacity and coordinates
    merged_station_numbers = list(merged.keys())
    result = await db.execute(
        select(Station).where(
            Station.station_number.in_(merged_station_numbers)
        )
    )
    station_map = {s.station_number: s for s in result.scalars().all()}

    # Auto-create minimal station records for readings whose stations
    # aren't in the DB yet (e.g. ECCC real-time reports a station that
    # isn't in the metadata collection). This ensures no readings are
    # lost — the station will be enriched on the next station sync.
    auto_created = 0
    # sn = station_number (e.g. "05AA004"), reading = NormalizedReading from provider
    for sn, reading in merged.items():
        if sn not in station_map:
            station = Station(
                station_number=sn,
                station_name=sn,  # Placeholder until next station sync
                data_source=reading.data_source,
                province=None,
            )
            db.add(station)
            station_map[sn] = station
            auto_created += 1

    if auto_created:
        await db.flush()  # Flush so FK references are valid
        logger.info(
            f"  Auto-created {auto_created} station records from readings"
        )

    merge_elapsed = time.monotonic() - merge_start
    logger.info(f"[2/3] Merge complete in {merge_elapsed:.1f}s")

    # ── Phase 3: Compute ratings and upsert readings ───────────────
    total_readings = len(merged)
    logger.info(f"[3/3] Computing ratings and upserting {total_readings} readings...")
    ratings_start = time.monotonic()

    target_date = datetime.now()
    upserted = 0

    # sn = station_number, reading = NormalizedReading from provider
    for sn, reading in merged.items():
        station = station_map.get(sn)

        # Compute flow rating (pcts = percentile thresholds from historical data)
        flow_value = reading.discharge or (
            reading.outflow if hasattr(reading, "outflow") else None
        )
        flow_pcts = await get_percentiles_for_station(
            db, sn, "flow", target_date
        )
        flow_rating = rate_value(flow_value, flow_pcts)

        # Compute level rating
        level_pcts = await get_percentiles_for_station(
            db, sn, "level", target_date
        )
        level_rating = rate_value(reading.water_level, level_pcts)

        # Reservoir fullness rating
        pct_full_val = (
            reading.pct_full if hasattr(reading, "pct_full") else None
        )
        pct_full_rating = None
        if station and station.has_capacity and pct_full_val is not None:
            pct_full_rating = rate_pct_full(pct_full_val)

        # Build the row values for upsert
        row = {
            "station_number": sn,
            "datetime_utc": reading.datetime_utc,
            "data_source": reading.data_source,
            "water_level": reading.water_level,
            "discharge": reading.discharge,
            "level_symbol": (
                reading.level_symbol
                if hasattr(reading, "level_symbol") else None
            ),
            "discharge_symbol": (
                reading.discharge_symbol
                if hasattr(reading, "discharge_symbol") else None
            ),
            "outflow": (
                reading.outflow if hasattr(reading, "outflow") else None
            ),
            "capacity": (
                reading.capacity if hasattr(reading, "capacity") else None
            ),
            "pct_full": pct_full_val,
            "flow_rating": flow_rating,
            "level_rating": level_rating,
            "pct_full_rating": pct_full_rating,
            "flow_percentiles": flow_pcts,
            "level_percentiles": level_pcts,
            "extra": reading.extra if reading.extra else None,
        }

        stmt = insert(CurrentReading).values(**row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_current_readings_station_number",
            set_={
                "datetime_utc": stmt.excluded.datetime_utc,
                "data_source": stmt.excluded.data_source,
                "water_level": stmt.excluded.water_level,
                "discharge": stmt.excluded.discharge,
                "level_symbol": stmt.excluded.level_symbol,
                "discharge_symbol": stmt.excluded.discharge_symbol,
                "outflow": stmt.excluded.outflow,
                "capacity": stmt.excluded.capacity,
                "pct_full": stmt.excluded.pct_full,
                "flow_rating": stmt.excluded.flow_rating,
                "level_rating": stmt.excluded.level_rating,
                "pct_full_rating": stmt.excluded.pct_full_rating,
                "flow_percentiles": stmt.excluded.flow_percentiles,
                "level_percentiles": stmt.excluded.level_percentiles,
                "extra": stmt.excluded.extra,
                "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        await db.execute(stmt)
        upserted += 1

        if upserted % 200 == 0 or upserted == total_readings:
            logger.info(
                f"  Ratings progress: {upserted}/{total_readings} readings"
            )

    await db.commit()

    ratings_elapsed = time.monotonic() - ratings_start
    total_elapsed = time.monotonic() - total_start
    logger.info(f"[3/3] Ratings and upsert complete in {ratings_elapsed:.1f}s")

    summary = {
        "readings_stored": upserted,
        "stations_auto_created": auto_created,
        "elapsed_seconds": round(total_elapsed, 1),
        "timing": {
            "fetch_seconds": round(fetch_elapsed, 1),
            "merge_seconds": round(merge_elapsed, 1),
            "ratings_seconds": round(ratings_elapsed, 1),
        },
        "providers": {
            name: len(readings)
            for name, readings in all_provider_readings
        },
    }
    logger.info(f"Readings refresh complete in {total_elapsed:.1f}s: {summary}")
    return summary
