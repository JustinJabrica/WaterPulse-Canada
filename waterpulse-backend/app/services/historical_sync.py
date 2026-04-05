"""
Historical data sync orchestrator.

Fetches daily mean flow/level from all providers and upserts into
historical_daily_means. Keyed by (station_number, data_key, month_day,
year) — duplicates are overwritten via ON CONFLICT UPDATE.

Run frequency: Jan 1st 03:00 UTC (CronJob in K8s, APScheduler in
Docker Compose), plus on demand via admin endpoint.

Design:
  - Short-lived DB sessions per operation (avoids idle connection drops)
  - Shared httpx client per provider (connection pooling)
  - Concurrent fetches via asyncio semaphore (MAX_CONCURRENCY)
  - Extended timeout (HISTORICAL_REQUEST_TIMEOUT = 180s)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database import async_session
from app.models.station import Station
from app.models.historical import HistoricalDailyMean
from app.services.providers import get_active_providers
from app.services.providers.base_provider import NormalizedDailyMean

logger = logging.getLogger(__name__)

MAX_YEARS = 5
MAX_CONCURRENCY = 20
INSERT_BATCH_SIZE = 200  # Rows per INSERT to avoid oversized statements


async def _fetch_station_history(
    provider,
    station_number: str,
    start_date: datetime,
    end_date: datetime,
    semaphore: asyncio.Semaphore,
    client=None,
) -> list[NormalizedDailyMean]:
    """Fetch historical data for one station with concurrency control."""
    async with semaphore:
        try:
            return await provider.fetch_historical_daily_means(
                station_number, start_date, end_date, client=client
            )
        except Exception as e:
            logger.warning(
                f"{provider.name}: {station_number} historical fetch failed: "
                f"{type(e).__name__}: {e}"
            )
            return []


def _daily_means_to_rows(
    means: list[NormalizedDailyMean],
) -> list[dict]:
    """
    Convert NormalizedDailyMean objects into DB rows. Each daily mean
    can produce up to two rows: one for flow, one for level.
    """
    rows = []
    # m = a single NormalizedDailyMean (one day's mean flow/level for one station)
    for m in means:
        if m.mean_flow is not None:
            rows.append({
                "station_number": m.station_number,
                "data_key": "flow",
                "month_day": m.month_day,
                "year": m.year,
                "value": m.mean_flow,
                "data_source": m.data_source,
            })
        if m.mean_level is not None:
            rows.append({
                "station_number": m.station_number,
                "data_key": "level",
                "month_day": m.month_day,
                "year": m.year,
                "value": m.mean_level,
                "data_source": m.data_source,
            })
    return rows


async def _sync_province(
    province: str,
) -> dict:
    """
    Sync historical data for one province. Each DB operation uses
    its own short-lived session to avoid idle connection drops.
    """
    province_start = time.monotonic()
    logger.info(f"  [{province}] Starting historical sync...")

    # Fetch 5 years for percentile calculations; older data is pruned
    end_date = datetime.now()
    start_date = end_date - timedelta(
        days=365 * settings.HISTORICAL_LOOKBACK_YEARS
    )

    # Get R/L stations for this province — short-lived session
    async with async_session() as read_db:
        result = await read_db.execute(
            select(Station).where(
                Station.station_type.in_(["R", "L"]),
                Station.province == province,
            )
        )
        stations = result.scalars().all()

    if not stations:
        logger.info(f"  [{province}] No R/L stations found, skipping")
        return {
            "province": province,
            "stations_processed": 0,
            "stations_with_data": 0,
            "rows_upserted": 0,
            "elapsed_seconds": 0,
        }

    logger.info(f"  [{province}] Found {len(stations)} R/L stations")

    providers = get_active_providers()
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    total_rows = 0
    stations_with_data = 0

    for provider in providers:
        # Filter to stations this provider handles
        provider_stations = [
            s for s in stations
            if s.data_source == provider.name
            or s.data_source == "both"
        ]

        if not provider_stations:
            continue

        provider_start = time.monotonic()
        logger.info(
            f"  [{province}] {provider.name}: "
            f"syncing {len(provider_stations)} stations"
        )

        # Shared client for connection pooling; extended timeout for large responses
        async with httpx.AsyncClient(
            timeout=settings.HISTORICAL_REQUEST_TIMEOUT,
        ) as client:
            tasks = [
                _fetch_station_history(
                    provider, s.station_number, start_date, end_date,
                    semaphore, client=client,
                )
                for s in provider_stations
            ]

            completed = 0
            for coro in asyncio.as_completed(tasks):
                means = await coro
                completed += 1

                if means:
                    rows = _daily_means_to_rows(means)
                    if rows:
                        # Batch inserts to keep statements small (avoids connection drops)
                        for i in range(0, len(rows), INSERT_BATCH_SIZE):
                            batch = rows[i : i + INSERT_BATCH_SIZE]
                            async with async_session() as write_db:
                                stmt = insert(HistoricalDailyMean).values(batch)
                                stmt = stmt.on_conflict_do_update(
                                    constraint="uq_station_key_date_year",
                                    set_={
                                        "value": stmt.excluded.value,
                                        "data_source": stmt.excluded.data_source,
                                    },
                                )
                                await write_db.execute(stmt)
                                await write_db.commit()
                        total_rows += len(rows)
                        stations_with_data += 1

                if completed % 10 == 0 or completed == len(tasks):
                    elapsed_so_far = time.monotonic() - provider_start
                    logger.info(
                        f"    [{province}] Progress: "
                        f"{completed} / {len(tasks)} stations "
                        f"({elapsed_so_far:.1f}s elapsed)"
                    )

        provider_elapsed = time.monotonic() - provider_start
        logger.info(
            f"  [{province}] {provider.name} complete in {provider_elapsed:.1f}s"
        )

    province_elapsed = time.monotonic() - province_start
    province_summary = {
        "province": province,
        "stations_processed": len(stations),
        "stations_with_data": stations_with_data,
        "rows_upserted": total_rows,
        "elapsed_seconds": round(province_elapsed, 1),
    }
    logger.info(f"  [{province}] Done in {province_elapsed:.1f}s: {province_summary}")
    return province_summary


async def sync_historical_data(
    province: str | None = None,
) -> dict:
    """
    Fetch historical daily means and upsert into the database.
    Syncs one province if given, otherwise all provinces sequentially.
    All DB operations use short-lived sessions internally.
    """
    total_start = time.monotonic()
    logger.info("Starting historical data sync...")

    if province:
        provinces_to_sync = [province.upper()]
    else:
        # Get all provinces that have R/L stations in the database
        async with async_session() as query_db:
            result = await query_db.execute(
                select(Station.province)
                .where(
                    Station.station_type.in_(["R", "L"]),
                    Station.province.isnot(None),
                )
                .group_by(Station.province)
                .order_by(Station.province)
            )
            provinces_to_sync = [row[0] for row in result.all()]

    logger.info(
        f"Syncing {len(provinces_to_sync)} province(s): "
        f"{', '.join(provinces_to_sync)}"
    )

    # Sync each province sequentially
    province_results = []
    total_stations = 0
    total_with_data = 0
    total_rows = 0

    for index, prov in enumerate(provinces_to_sync, 1):
        logger.info(
            f"Province {index}/{len(provinces_to_sync)}: {prov}"
        )
        result = await _sync_province(prov)
        province_results.append(result)
        total_stations += result["stations_processed"]
        total_with_data += result["stations_with_data"]
        total_rows += result["rows_upserted"]

        running_elapsed = time.monotonic() - total_start
        logger.info(
            f"Completed {index}/{len(provinces_to_sync)} provinces "
            f"({running_elapsed:.1f}s elapsed, "
            f"{total_rows} total rows so far)"
        )

    # Prune data older than MAX_YEARS
    logger.info("Pruning old historical data...")
    prune_start = time.monotonic()
    async with async_session() as prune_db:
        pruned = await _prune_old_data(prune_db)
    prune_elapsed = time.monotonic() - prune_start

    total_elapsed = time.monotonic() - total_start

    summary = {
        "provinces_synced": len(provinces_to_sync),
        "stations_processed": total_stations,
        "stations_with_data": total_with_data,
        "rows_upserted": total_rows,
        "rows_pruned": pruned,
        "elapsed_seconds": round(total_elapsed, 1),
        "timing": {
            "sync_seconds": round(total_elapsed - prune_elapsed, 1),
            "prune_seconds": round(prune_elapsed, 1),
        },
        "by_province": province_results,
    }
    logger.info(f"Historical sync complete in {total_elapsed:.1f}s: {summary}")
    return summary


async def _prune_old_data(db: AsyncSession) -> int:
    """Remove historical data older than MAX_YEARS per station/key/date."""
    result = await db.execute(
        select(
            HistoricalDailyMean.station_number,
            HistoricalDailyMean.data_key,
            HistoricalDailyMean.month_day,
        )
        .group_by(
            HistoricalDailyMean.station_number,
            HistoricalDailyMean.data_key,
            HistoricalDailyMean.month_day,
        )
        .having(func.count() > MAX_YEARS)
    )
    groups = result.all()

    pruned = 0
    # sn = station_number, dk = data_key ("flow"/"level"), md = month_day ("MM-DD")
    for sn, dk, md in groups:
        year_result = await db.execute(
            select(HistoricalDailyMean.year)
            .where(
                HistoricalDailyMean.station_number == sn,
                HistoricalDailyMean.data_key == dk,
                HistoricalDailyMean.month_day == md,
            )
            .order_by(HistoricalDailyMean.year.desc())
            .limit(MAX_YEARS)
        )
        keep_years = [row[0] for row in year_result.all()]

        del_result = await db.execute(
            delete(HistoricalDailyMean).where(
                HistoricalDailyMean.station_number == sn,
                HistoricalDailyMean.data_key == dk,
                HistoricalDailyMean.month_day == md,
                HistoricalDailyMean.year.notin_(keep_years),
            )
        )
        pruned += del_result.rowcount

    if pruned > 0:
        await db.commit()
        logger.info(f"Pruned {pruned} old historical records")

    return pruned
