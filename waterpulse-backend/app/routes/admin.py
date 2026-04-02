"""
Admin routes for triggering background data sync tasks.

These endpoints handle station sync, historical data download,
manual readings refresh, and system status information.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.station import Station
from app.models.reading import CurrentReading
from app.models.historical import HistoricalDailyMean
from app.services.station_sync import sync_stations
from app.services.historical_sync import sync_historical_data
from app.services.readings_refresh import refresh_current_readings

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/sync-stations")
async def trigger_station_sync(db: AsyncSession = Depends(get_db)):
    """
    Fetch stations from all providers and update the database.
    Run this twice per year or when stations change.
    """
    summary = await sync_stations(db)
    return {"status": "complete", **summary}


@router.post("/sync-historical")
async def trigger_historical_sync(
    province: str | None = Query(None, description="Filter to a single province (e.g., AB, BC, ON)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch historical daily means from all providers.
    Pass ?province=AB to sync one province at a time instead of all of Canada.
    """
    summary = await sync_historical_data(db, province=province)
    return {"status": "complete", **summary}


@router.post("/refresh-readings")
async def trigger_readings_refresh(
    province: str | None = Query(None, description="Refresh only this province (e.g., AB, BC, ON)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a full readings refresh via admin.
    For selective refresh, use POST /api/readings/refresh instead.
    """
    summary = await refresh_current_readings(db, province=province)
    return {"status": "complete", **summary}


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    """Get system status including data counts, freshness, and breakdowns."""

    # Station counts
    station_count = await db.execute(
        select(func.count()).select_from(Station)
    )
    total_stations = station_count.scalar()

    # By type
    type_counts = await db.execute(
        select(Station.station_type, func.count())
        .group_by(Station.station_type)
    )
    station_types = {row[0] or "None": row[1] for row in type_counts.all()}

    # By province
    province_counts = await db.execute(
        select(Station.province, func.count())
        .group_by(Station.province)
        .order_by(Station.province)
    )
    by_province = {row[0] or "None": row[1] for row in province_counts.all()}

    # By data source
    source_counts = await db.execute(
        select(Station.data_source, func.count())
        .group_by(Station.data_source)
    )
    by_source = {row[0] or "None": row[1] for row in source_counts.all()}

    # Current readings
    reading_count = await db.execute(
        select(func.count()).select_from(CurrentReading)
    )
    total_readings = reading_count.scalar()

    latest_fetch = await db.execute(
        select(func.max(CurrentReading.fetched_at))
    )
    last_updated = latest_fetch.scalar()

    # Reading source breakdown
    reading_source_counts = await db.execute(
        select(CurrentReading.data_source, func.count())
        .group_by(CurrentReading.data_source)
    )
    readings_by_source = {
        row[0] or "None": row[1] for row in reading_source_counts.all()
    }

    # Historical data
    hist_count = await db.execute(
        select(func.count()).select_from(HistoricalDailyMean)
    )
    total_historical = hist_count.scalar()

    hist_stations = await db.execute(
        select(func.count(HistoricalDailyMean.station_number.distinct()))
    )
    stations_with_history = hist_stations.scalar()

    hist_years = await db.execute(
        select(
            func.min(HistoricalDailyMean.year),
            func.max(HistoricalDailyMean.year),
        )
    )
    year_range = hist_years.one()

    return {
        "stations": {
            "total": total_stations,
            "by_type": station_types,
            "by_province": by_province,
            "by_source": by_source,
        },
        "current_readings": {
            "total": total_readings,
            "by_source": readings_by_source,
            "last_updated": last_updated.isoformat() if last_updated else None,
        },
        "historical_data": {
            "total_records": total_historical,
            "stations_with_data": stations_with_history,
            "year_range": {
                "min": year_range[0],
                "max": year_range[1],
            } if year_range[0] else None,
        },
        "server_time": datetime.now().isoformat(),
    }
