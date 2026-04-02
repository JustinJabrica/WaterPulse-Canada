from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.station import Station
from app.models.reading import CurrentReading
from app.schemas import CurrentReadingResponse, StationWithReading
from app.services.readings_refresh import refresh_current_readings

router = APIRouter(prefix="/api/readings", tags=["readings"])


# ── Helper ──────────────────────────────────────────────────────────


async def _build_station_readings(
    stations: list,
    db: AsyncSession,
) -> list[StationWithReading]:
    """Pair each station with its latest reading.

    Builds the full StationWithReading response including all fields
    from the Station model (province, data_source, drainage_basin_prefix, etc.).
    """
    results = []
    # station = Station DB model
    for station in stations:
        reading_result = await db.execute(
            select(CurrentReading)
            .where(CurrentReading.station_number == station.station_number)
            .order_by(CurrentReading.fetched_at.desc())
            .limit(1)
        )
        reading = reading_result.scalar_one_or_none()

        results.append(
            StationWithReading(
                station_number=station.station_number,
                station_name=station.station_name,
                latitude=station.latitude,
                longitude=station.longitude,
                province=station.province,
                station_type=station.station_type,
                data_type=station.data_type,
                data_source=station.data_source,
                basin_number=station.basin_number,
                catchment_number=station.catchment_number,
                drainage_basin_prefix=station.drainage_basin_prefix,
                has_capacity=station.has_capacity or False,
                latest_reading=reading,
            )
        )
    return results


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/refresh")
async def trigger_refresh(
    station_numbers: List[str] | None = Query(
        None, description="Specific station numbers to refresh (e.g. 05AA004)"
    ),
    province: str | None = Query(
        None, description="Refresh all stations in a province (e.g. AB, BC, ON)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an on-demand readings refresh.

    The frontend calls this to fetch fresh data from external APIs,
    compute ratings and weather, and upsert into the database.

    Filters (pick one or neither):
        - station_numbers: refresh only these specific stations
        - province: refresh all stations in one province
        - neither: refresh all stations across Canada
    """
    summary = await refresh_current_readings(
        db,
        station_numbers=station_numbers,
        province=province,
    )
    return {"status": "complete", **summary}


@router.get("/last-updated")
async def get_last_updated(db: AsyncSession = Depends(get_db)):
    """Get the timestamp of the most recent data refresh."""
    result = await db.execute(
        select(func.max(CurrentReading.fetched_at))
    )
    last_updated = result.scalar()
    return {
        "last_updated": last_updated.isoformat() if last_updated else None,
        "server_time": datetime.now().isoformat(),
    }


@router.get("/by-basin/{basin_number}", response_model=list[StationWithReading])
async def get_readings_by_basin(
    basin_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all current readings for stations in a basin."""
    result = await db.execute(
        select(Station)
        .where(
            Station.basin_number == basin_number.upper(),
            Station.station_type.in_(["R", "L"]),
        )
        .order_by(Station.station_number)
    )
    return await _build_station_readings(result.scalars().all(), db)


@router.get("/by-catchment/{catchment}", response_model=list[StationWithReading])
async def get_readings_by_catchment(
    catchment: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all current readings for stations in a catchment group."""
    result = await db.execute(
        select(Station)
        .where(
            Station.catchment_number == catchment.upper(),
            Station.station_type.in_(["R", "L"]),
        )
        .order_by(Station.station_number)
    )
    return await _build_station_readings(result.scalars().all(), db)


@router.get("/by-province/{province_code}", response_model=list[StationWithReading])
async def get_readings_by_province(
    province_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all current readings for stations in a province."""
    result = await db.execute(
        select(Station)
        .where(
            Station.province == province_code.upper(),
            Station.station_type.in_(["R", "L"]),
        )
        .order_by(Station.station_number)
    )
    return await _build_station_readings(result.scalars().all(), db)


@router.get(
    "/by-drainage-basin/{prefix}",
    response_model=list[StationWithReading],
)
async def get_readings_by_drainage_basin(
    prefix: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all current readings for a national drainage basin.

    The prefix is the first two digits of the station number (e.g. 05,
    07, 08) which identifies the major drainage basin across Canada.
    """
    result = await db.execute(
        select(Station)
        .where(
            Station.drainage_basin_prefix == prefix.upper(),
            Station.station_type.in_(["R", "L"]),
        )
        .order_by(Station.station_number)
    )
    return await _build_station_readings(result.scalars().all(), db)


@router.get("/all", response_model=list[StationWithReading])
async def get_all_readings(
    station_type: str | None = Query(None, description="Filter: R or L"),
    province: str | None = Query(None, description="Filter by province code (e.g., AB, BC, ON)"),
    db: AsyncSession = Depends(get_db),
):
    """Get all current readings. Optionally filter by station type and province."""
    query = select(Station).where(Station.station_type.in_(["R", "L"]))
    if station_type:
        query = select(Station).where(Station.station_type == station_type.upper())
    if province:
        query = query.where(Station.province == province.upper())

    result = await db.execute(query.order_by(Station.station_number))
    return await _build_station_readings(result.scalars().all(), db)
