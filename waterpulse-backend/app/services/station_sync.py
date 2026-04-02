"""
Station sync orchestrator.

Loops all registered providers, merges station metadata with
Alberta-priority logic, and upserts into the stations table.

Merge rules for shared stations (same station_number in both APIs):
    - Alberta wins: station_name, station_type, basin_number, catchment_number,
      data_type, has_capacity, parameter_data_status, extra
    - ECCC fills in: status, drainage_area_gross, drainage_area_effect,
      contributor, vertical_datum, rhbn
    - data_source set to "both"

Run frequency: Twice per year or on demand via admin endpoint.
"""

import logging
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station
from app.services.providers import get_active_providers
from app.services.providers.base_provider import NormalizedStation

logger = logging.getLogger(__name__)


def _merge_stations(
    all_provider_stations: list[tuple[str, list[NormalizedStation]]],
) -> dict[str, dict]:
    """
    Merge station lists from all providers into a single dict keyed by
    station_number. Providers are processed in registration order
    (Alberta first), so first-write wins for Alberta-priority fields.
    """
    merged: dict[str, dict] = {}

    for provider_name, stations in all_provider_stations:
        # s = NormalizedStation from a provider (parsed API data, not a DB model)
        for s in stations:
            existing = merged.get(s.station_number)

            if existing is None:
                # First time seeing this station — take everything
                merged[s.station_number] = {
                    "station_number": s.station_number,
                    "station_name": s.station_name,
                    "data_source": s.data_source,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "province": s.province,
                    "station_type": s.station_type,
                    "data_type": s.data_type,
                    "basin_number": s.basin_number,
                    "catchment_number": s.catchment_number,
                    "drainage_basin_prefix": s.drainage_basin_prefix,
                    "status": s.status,
                    "real_time": s.real_time,
                    "drainage_area_gross": s.drainage_area_gross,
                    "drainage_area_effect": s.drainage_area_effect,
                    "contributor": s.contributor,
                    "vertical_datum": s.vertical_datum,
                    "rhbn": s.rhbn,
                    "has_capacity": s.has_capacity or False,
                    "parameter_data_status": s.parameter_data_status,
                    "extra": s.extra,
                }
            else:
                # Shared station — mark as "both", fill in missing fields
                existing["data_source"] = "both"

                # ECCC fills in fields Alberta doesn't have
                if existing.get("status") is None and s.status is not None:
                    existing["status"] = s.status
                if existing.get("drainage_area_gross") is None and s.drainage_area_gross is not None:
                    existing["drainage_area_gross"] = s.drainage_area_gross
                if existing.get("drainage_area_effect") is None and s.drainage_area_effect is not None:
                    existing["drainage_area_effect"] = s.drainage_area_effect
                if existing.get("contributor") is None and s.contributor is not None:
                    existing["contributor"] = s.contributor
                if existing.get("vertical_datum") is None and s.vertical_datum is not None:
                    existing["vertical_datum"] = s.vertical_datum
                if existing.get("rhbn") is None and s.rhbn is not None:
                    existing["rhbn"] = s.rhbn
                if existing.get("real_time") is None and s.real_time is not None:
                    existing["real_time"] = s.real_time
                if existing.get("drainage_basin_prefix") is None and s.drainage_basin_prefix is not None:
                    existing["drainage_basin_prefix"] = s.drainage_basin_prefix

    return merged


async def sync_stations(db: AsyncSession) -> dict:
    """
    Fetch stations from all providers, merge, and upsert into the database.
    Returns a summary dict with counts.
    """
    logger.info("Starting station sync across all providers...")
    total_start = time.monotonic()

    # ── Phase 1: Fetch from providers ──────────────────────────────
    logger.info("[1/3] Fetching stations from providers...")
    fetch_start = time.monotonic()

    all_provider_stations: list[tuple[str, list[NormalizedStation]]] = []
    providers = get_active_providers()

    for provider in providers:
        try:
            stations = await provider.fetch_stations()
            all_provider_stations.append((provider.name, stations))
            logger.info(f"  {provider.name}: {len(stations)} stations fetched")
        except Exception as e:
            logger.error(f"  {provider.name}: fetch failed: {e}", exc_info=True)

    fetch_elapsed = time.monotonic() - fetch_start
    logger.info(f"[1/3] Fetch complete in {fetch_elapsed:.1f}s")

    # ── Phase 2: Merge with priority order (Alberta first) ────────
    logger.info("[2/3] Merging station data...")
    merge_start = time.monotonic()

    merged = _merge_stations(all_provider_stations)

    merge_elapsed = time.monotonic() - merge_start
    logger.info(
        f"[2/3] Merged into {len(merged)} unique stations in {merge_elapsed:.1f}s"
    )

    # ── Phase 3: Upsert into database ─────────────────────────────
    logger.info(f"[3/3] Upserting {len(merged)} stations to database...")
    upsert_start = time.monotonic()

    created = 0
    updated = 0
    total = len(merged)

    for index, station_data in enumerate(merged.values(), 1):
        sn = station_data["station_number"]  # sn = station_number (e.g. "05AA004")

        result = await db.execute(
            select(Station).where(Station.station_number == sn)
        )
        station = result.scalar_one_or_none()

        if station is None:
            station = Station(station_number=sn)
            created += 1
        else:
            updated += 1

        # Apply all fields from merged data
        station.station_name = station_data["station_name"]
        station.data_source = station_data["data_source"]
        station.latitude = station_data["latitude"]
        station.longitude = station_data["longitude"]
        station.province = station_data["province"]
        station.station_type = station_data["station_type"]
        station.data_type = station_data["data_type"]
        station.basin_number = station_data["basin_number"]
        station.catchment_number = station_data["catchment_number"]
        station.drainage_basin_prefix = station_data["drainage_basin_prefix"]
        station.status = station_data["status"]
        station.real_time = station_data["real_time"]
        station.drainage_area_gross = station_data["drainage_area_gross"]
        station.drainage_area_effect = station_data["drainage_area_effect"]
        station.contributor = station_data["contributor"]
        station.vertical_datum = station_data["vertical_datum"]
        station.rhbn = station_data["rhbn"]
        station.has_capacity = station_data["has_capacity"]
        station.parameter_data_status = station_data["parameter_data_status"]
        station.extra = station_data["extra"]

        db.add(station)

        if index % 200 == 0 or index == total:
            logger.info(f"  Upsert progress: {index}/{total} stations")

    await db.commit()

    upsert_elapsed = time.monotonic() - upsert_start
    total_elapsed = time.monotonic() - total_start
    logger.info(f"[3/3] Upsert complete in {upsert_elapsed:.1f}s")

    summary = {
        "total_merged": len(merged),
        "created": created,
        "updated": updated,
        "elapsed_seconds": round(total_elapsed, 1),
        "timing": {
            "fetch_seconds": round(fetch_elapsed, 1),
            "merge_seconds": round(merge_elapsed, 1),
            "upsert_seconds": round(upsert_elapsed, 1),
        },
        "providers": {
            name: len(stations)
            for name, stations in all_provider_stations
        },
    }
    logger.info(f"Station sync complete in {total_elapsed:.1f}s: {summary}")
    return summary
