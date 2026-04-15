import math
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.station import Station
from app.models.reading import CurrentReading
from app.models.weather import StationWeather
from app.schemas import (
    StationResponse,
    StationSummary,
    StationWithReading,
    StationWeatherResponse,
    CurrentReadingResponse,
    StationGroup,
    BasinInfo,
    ProvinceInfo,
)
from app.routes.readings import _build_station_readings
from app.services.weather_cache import get_station_weather

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("/", response_model=list[StationSummary])
async def list_stations(
    station_type: str | None = Query(None, description="Filter by station type (R, L, M)"),
    basin: str | None = Query(None, description="Filter by basin number (e.g., BOW)"),
    catchment: str | None = Query(None, description="Filter by catchment prefix (e.g., 05BH)"),
    province: str | None = Query(None, description="Filter by province code (e.g., AB, BC, ON)"),
    db: AsyncSession = Depends(get_db),
):
    """List all stations with optional filters."""
    query = select(Station)
    if station_type:
        query = query.where(Station.station_type == station_type.upper())
    if basin:
        query = query.where(Station.basin_number == basin.upper())
    if catchment:
        query = query.where(Station.catchment_number == catchment.upper())
    if province:
        query = query.where(Station.province == province.upper())

    query = query.order_by(Station.station_number)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/basins", response_model=list[BasinInfo])
async def list_basins(db: AsyncSession = Depends(get_db)):
    """List all basins with their station groups and counts."""
    result = await db.execute(
        select(Station).order_by(Station.station_number)
    )
    stations = result.scalars().all()

    # Group by basin -> catchment
    # s = Station DB model
    basin_groups: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for s in stations:
        basin = s.basin_number or "Unknown"
        catchment = s.catchment_number or "Unknown"
        basin_groups[basin][catchment].append(s)

    basins = []
    for basin_number in sorted(basin_groups.keys()):
        catchments = basin_groups[basin_number]
        groups = []
        total = 0
        for prefix in sorted(catchments.keys()):
            group_stations = catchments[prefix]
            total += len(group_stations)
            groups.append(
                StationGroup(
                    prefix=prefix,
                    basin_number=basin_number,
                    station_count=len(group_stations),
                    sample_names=[s.station_name for s in group_stations[:3]],
                )
            )
        basins.append(
            BasinInfo(
                basin_number=basin_number,
                total_stations=total,
                group_count=len(groups),
                groups=groups,
            )
        )

    return basins


@router.get("/provinces", response_model=list[ProvinceInfo])
async def list_provinces(db: AsyncSession = Depends(get_db)):
    """List all provinces with station counts and type breakdown."""
    # Only count River (R) and Lake/Reservoir (L) stations — meteorological
    # stations are excluded because the dashboard's by-province endpoint
    # only returns R and L types, so the counts here must match.
    # LEFT JOIN on current_readings so we can also report how many stations
    # currently have a reading (used by the map's per-province cluster sizing
    # when the "show inactive" toggle is off).
    result = await db.execute(
        select(
            Station.province,
            Station.station_type,
            func.count(Station.station_number).label("count"),
            func.count(CurrentReading.station_number).label("with_reading"),
        )
        .select_from(Station)
        .outerjoin(CurrentReading, CurrentReading.station_number == Station.station_number)
        .where(
            Station.province.isnot(None),
            Station.station_type.in_(["R", "L"]),
        )
        .group_by(Station.province, Station.station_type)
    )
    rows = result.all()

    # Group counts by province
    # province_code = 2-letter province abbreviation (e.g. "AB", "BC")
    province_data: dict[str, dict] = {}
    for province_code, station_type, count, with_reading in rows:
        if province_code not in province_data:
            province_data[province_code] = {
                "province_code": province_code,
                "total_stations": 0,
                "river_count": 0,
                "lake_count": 0,
                "met_count": 0,
                "river_with_reading": 0,
                "lake_with_reading": 0,
            }
        entry = province_data[province_code]
        entry["total_stations"] += count
        if station_type == "R":
            entry["river_count"] = count
            entry["river_with_reading"] = with_reading
        elif station_type == "L":
            entry["lake_count"] = count
            entry["lake_with_reading"] = with_reading
        elif station_type == "M":
            entry["met_count"] = count

    return [
        ProvinceInfo(**data)
        for data in sorted(province_data.values(), key=lambda d: d["province_code"])
    ]


@router.get("/search", response_model=list[StationWithReading])
async def search_stations(
    q: str = Query(..., min_length=2, description="Search term for station name"),
    province: str | None = Query(None, description="Filter by province code (e.g., AB, BC, ON)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db),
):
    """Search stations by name (case-insensitive partial match).

    Returns each station paired with its latest reading so search
    results display flow, level, and capacity data on the cards.
    Optionally scoped to a single province.
    """
    # Only search River (R) and Lake/Reservoir (L) stations — meteorological
    # stations are excluded from all dashboard and readings endpoints.
    # selectinload eagerly fetches the related current_readings in a single
    # batch query instead of one query per station (avoids N+1).
    query = (
        select(Station)
        .where(
            Station.station_name.ilike(f"%{q}%"),
            Station.station_type.in_(["R", "L"]),
        )
        .options(selectinload(Station.current_readings))
    )
    if province:
        query = query.where(Station.province == province.upper())
    query = query.order_by(Station.station_name).limit(limit)
    result = await db.execute(query)
    stations = result.scalars().all()

    # Build response — readings already loaded via selectinload
    return [
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
            latest_reading=station.current_readings[0] if station.current_readings else None,
        )
        for station in stations
    ]


@router.get("/nearby", response_model=list[StationSummary])
async def nearby_stations(
    lat: float = Query(..., description="Latitude of search centre"),
    lon: float = Query(..., description="Longitude of search centre"),
    radius: float = Query(50, ge=1, le=500, description="Search radius in kilometres"),
    limit: int = Query(25, ge=1, le=100, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db),
):
    """Find stations within a radius of a given point.

    Uses the equirectangular approximation for distance, which is accurate
    enough for the distances involved (under 500 km). Stations without
    coordinates are excluded.
    """
    # Pre-filter with a bounding box to reduce the number of rows
    # before computing distances. 1 degree of latitude is roughly 111 km.
    lat_offset = radius / 111.0
    lon_offset = radius / (111.0 * math.cos(math.radians(lat)))

    result = await db.execute(
        select(Station).where(
            Station.latitude.isnot(None),
            Station.longitude.isnot(None),
            Station.latitude.between(lat - lat_offset, lat + lat_offset),
            Station.longitude.between(lon - lon_offset, lon + lon_offset),
        )
    )
    candidates = result.scalars().all()

    # Compute actual distance and filter/sort
    # station = Station DB model with latitude/longitude
    stations_with_distance = []
    for station in candidates:
        # Equirectangular distance in kilometres
        delta_lat = math.radians(station.latitude - lat)
        delta_lon = math.radians(station.longitude - lon) * math.cos(
            math.radians((lat + station.latitude) / 2)
        )
        distance_km = math.sqrt(delta_lat**2 + delta_lon**2) * 6371

        if distance_km <= radius:
            stations_with_distance.append((station, distance_km))

    stations_with_distance.sort(key=lambda pair: pair[1])
    return [station for station, _distance in stations_with_distance[:limit]]


@router.get("/bbox", response_model=list[StationWithReading])
async def stations_in_bbox(
    min_lat: float = Query(..., description="Southern boundary latitude"),
    max_lat: float = Query(..., description="Northern boundary latitude"),
    min_lon: float = Query(..., description="Western boundary longitude"),
    max_lon: float = Query(..., description="Eastern boundary longitude"),
    province: str | None = Query(None, description="Filter by province code (e.g., AB, BC, ON)"),
    station_type: str | None = Query(None, description="Filter by station type (R or L)"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db),
):
    """Return stations within a bounding box, each paired with its latest reading.

    Used by the interactive map to load stations for the current viewport.
    Only River (R) and Lake/Reservoir (L) stations are returned.
    """
    query = (
        select(Station)
        .where(
            Station.latitude.isnot(None),
            Station.longitude.isnot(None),
            Station.station_type.in_(["R", "L"]),
            Station.latitude.between(min_lat, max_lat),
            Station.longitude.between(min_lon, max_lon),
        )
        .options(selectinload(Station.current_readings))
    )
    if province:
        query = query.where(Station.province == province.upper())
    if station_type:
        query = query.where(Station.station_type == station_type.upper())
    query = query.order_by(Station.station_number).limit(limit)

    result = await db.execute(query)
    stations = result.scalars().all()
    return _build_station_readings(stations)


@router.get("/{station_number}/weather", response_model=StationWeatherResponse)
async def get_weather(station_number: str, db: AsyncSession = Depends(get_db)):
    """Get weather for a station. Returns cached data if fresh (< 30 min),
    otherwise fetches live from Open-Meteo and caches."""
    result = await db.execute(
        select(Station).where(Station.station_number == station_number)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    weather_data = await get_station_weather(db, station_number)

    # Get the cached timestamp
    cache_result = await db.execute(
        select(StationWeather.weather_fetched_at).where(
            StationWeather.station_number == station_number
        )
    )
    fetched_at = cache_result.scalar_one_or_none()

    return StationWeatherResponse(
        station_number=station_number,
        weather=weather_data,
        weather_fetched_at=fetched_at,
    )


@router.get("/{station_number}", response_model=StationResponse)
async def get_station(station_number: str, db: AsyncSession = Depends(get_db)):
    """Get detailed information for a single station."""
    result = await db.execute(
        select(Station).where(Station.station_number == station_number)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@router.get("/{station_number}/current", response_model=StationWithReading)
async def get_station_with_reading(
    station_number: str, db: AsyncSession = Depends(get_db)
):
    """Get a station with its most recent reading and rating."""
    result = await db.execute(
        select(Station).where(Station.station_number == station_number)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Get the latest reading
    reading_result = await db.execute(
        select(CurrentReading)
        .where(CurrentReading.station_number == station_number)
        .order_by(CurrentReading.fetched_at.desc())
        .limit(1)
    )
    reading = reading_result.scalar_one_or_none()

    return StationWithReading(
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
