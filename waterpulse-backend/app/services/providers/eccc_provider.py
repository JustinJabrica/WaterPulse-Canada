"""
ECCC Provider
==============
Fetches hydrometric data from Environment and Climate Change Canada's
OGC API at api.weather.gc.ca. Primary source for all of Canada.

Endpoints used:
    - hydrometric-stations/items     — station metadata (paginated by province)
    - hydrometric-realtime/items     — current readings (province by province)
    - hydrometric-daily-mean/items   — historical daily means (per station)

Response format: standard GeoJSON FeatureCollection.
Coordinates are [longitude, latitude] (GeoJSON order).
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.services.providers.base_provider import (
    BaseProvider,
    NormalizedStation,
    NormalizedReading,
    NormalizedDailyMean,
)

logger = logging.getLogger(__name__)


def _infer_station_type(station_name: str) -> str:
    """
    ECCC has no station_type field. Infer from name keywords.
    Returns "R" (river, default), "L" (lake/reservoir), or "M" (met).
    """
    upper = station_name.upper()
    if any(kw in upper for kw in ("LAKE", "RESERVOIR", "LAC ", "LAC-")):
        return "L"
    return "R"


class ECCCProvider(BaseProvider):
    """ECCC OGC API — federal hydrometric data for all of Canada."""

    @property
    def name(self) -> str:
        return "eccc"

    # ── Stations ────────────────────────────────────────────────────

    async def fetch_stations(self) -> list[NormalizedStation]:
        """
        Fetch all stations from ECCC, paginating by province.
        Returns normalized station objects with federal metadata.
        """
        all_stations: list[NormalizedStation] = []

        async with httpx.AsyncClient(
            timeout=settings.ECCC_REQUEST_TIMEOUT
        ) as client:
            for province in settings.PROVINCES:
                province_stations = await self._fetch_stations_for_province(
                    client, province
                )
                all_stations.extend(province_stations)

        logger.info(f"ECCC: fetched {len(all_stations)} stations total")
        return all_stations

    async def _fetch_stations_for_province(
        self,
        client: httpx.AsyncClient,
        province: str,
    ) -> list[NormalizedStation]:
        """Paginate through all stations for a single province."""
        stations: list[NormalizedStation] = []
        offset = 0

        while True:
            params = {
                "PROV_TERR_STATE_LOC": province,
                "limit": settings.ECCC_PAGE_SIZE,
                "offset": offset,
                "f": "json",
            }

            try:
                resp = await client.get(
                    settings.eccc_stations_url, params=params
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.error(f"ECCC stations {province} offset={offset}: {e}")
                break

            features = data.get("features", [])
            if not features:
                break

            for feature in features:
                station = self._parse_station_feature(feature, province)
                if station:
                    stations.append(station)

            # If we got fewer than page size, we've reached the end
            if len(features) < settings.ECCC_PAGE_SIZE:
                break
            offset += settings.ECCC_PAGE_SIZE

        logger.info(f"ECCC: {province} — {len(stations)} stations")
        return stations

    def _parse_station_feature(
        self, feature: dict, province: str
    ) -> NormalizedStation | None:
        """Parse a single GeoJSON feature into a NormalizedStation."""
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [None, None])

        station_number = props.get("STATION_NUMBER")
        station_name = props.get("STATION_NAME")
        if not station_number or not station_name:
            return None

        # GeoJSON coordinates are [longitude, latitude]
        longitude = coords[0] if len(coords) > 0 else None
        latitude = coords[1] if len(coords) > 1 else None

        # Derive drainage basin prefix from station number (first 2 chars)
        drainage_prefix = station_number[:2] if len(station_number) >= 2 else None

        return NormalizedStation(
            station_number=station_number,
            station_name=station_name,
            data_source=self.name,
            latitude=latitude,
            longitude=longitude,
            province=province,
            station_type=_infer_station_type(station_name),
            data_type="HG",  # ECCC hydrometric stations are water data
            drainage_basin_prefix=drainage_prefix,
            status=props.get("STATUS_EN"),
            real_time=props.get("REAL_TIME") == 1,
            drainage_area_gross=props.get("DRAINAGE_AREA_GROSS"),
            drainage_area_effect=props.get("DRAINAGE_AREA_EFFECT"),
            contributor=props.get("CONTRIBUTOR_EN"),
            vertical_datum=props.get("VERTICAL_DATUM"),
            rhbn=props.get("RHBN") == 1,
        )

    # ── Readings ────────────────────────────────────────────────────

    async def fetch_latest_readings(
        self,
        station_numbers: list[str] | None = None,
        province: str | None = None,
    ) -> list[NormalizedReading]:
        """
        Fetch current readings with a configurable datetime window,
        then deduplicate to keep only the latest per station.

        Filters:
            station_numbers — fetch only these stations (uses STATION_NUMBER param)
            province — fetch only one province instead of all 13
        """
        all_readings: dict[str, NormalizedReading] = {}

        async with httpx.AsyncClient(
            timeout=settings.ECCC_REQUEST_TIMEOUT
        ) as client:
            if station_numbers:
                # Fetch specific stations directly by station number
                readings = await self._fetch_readings_for_stations(
                    client, station_numbers
                )
                for reading in readings:
                    existing = all_readings.get(reading.station_number)
                    if existing is None or (
                        reading.datetime_utc
                        and existing.datetime_utc
                        and reading.datetime_utc > existing.datetime_utc
                    ):
                        all_readings[reading.station_number] = reading
            else:
                # Fetch by province (one or all)
                provinces = [province.upper()] if province else settings.PROVINCES
                for prov in provinces:
                    readings = await self._fetch_readings_for_province(
                        client, prov
                    )
                    for reading in readings:
                        existing = all_readings.get(reading.station_number)
                        if existing is None or (
                            reading.datetime_utc
                            and existing.datetime_utc
                            and reading.datetime_utc > existing.datetime_utc
                        ):
                            all_readings[reading.station_number] = reading

        logger.info(
            f"ECCC: {len(all_readings)} stations with current readings"
        )
        return list(all_readings.values())

    async def _fetch_readings_for_stations(
        self,
        client: httpx.AsyncClient,
        station_numbers: list[str],
    ) -> list[NormalizedReading]:
        """Fetch real-time readings for specific stations by number."""
        readings: list[NormalizedReading] = []

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(
            hours=settings.ECCC_REALTIME_WINDOW_HOURS
        )
        datetime_filter = (
            f"{window_start.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        for station_number in station_numbers:
            offset = 0
            while True:
                params = {
                    "STATION_NUMBER": station_number,
                    "datetime": datetime_filter,
                    "limit": settings.ECCC_PAGE_SIZE,
                    "offset": offset,
                    "f": "json",
                }

                try:
                    resp = await client.get(
                        settings.eccc_realtime_url, params=params
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    logger.warning(
                        f"ECCC reading {station_number}: {e}"
                    )
                    break

                features = data.get("features", [])
                if not features:
                    break

                for feature in features:
                    reading = self._parse_reading_feature(feature)
                    if reading:
                        readings.append(reading)

                if len(features) < settings.ECCC_PAGE_SIZE:
                    break
                offset += settings.ECCC_PAGE_SIZE

        return readings

    async def _fetch_readings_for_province(
        self,
        client: httpx.AsyncClient,
        province: str,
    ) -> list[NormalizedReading]:
        """Fetch real-time readings for a province."""
        readings: list[NormalizedReading] = []

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(
            hours=settings.ECCC_REALTIME_WINDOW_HOURS
        )
        datetime_filter = (
            f"{window_start.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
            f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        offset = 0
        while True:
            params = {
                "PROV_TERR_STATE_LOC": province,
                "datetime": datetime_filter,
                "limit": settings.ECCC_PAGE_SIZE,
                "offset": offset,
                "f": "json",
            }

            try:
                resp = await client.get(
                    settings.eccc_realtime_url, params=params
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.error(
                    f"ECCC readings {province} offset={offset}: {e}"
                )
                break

            features = data.get("features", [])
            if not features:
                break

            for feature in features:
                reading = self._parse_reading_feature(feature)
                if reading:
                    readings.append(reading)

            if len(features) < settings.ECCC_PAGE_SIZE:
                break
            offset += settings.ECCC_PAGE_SIZE

        return readings

    def _parse_reading_feature(
        self, feature: dict
    ) -> NormalizedReading | None:
        """Parse a single GeoJSON feature into a NormalizedReading."""
        props = feature.get("properties", {})

        station_number = props.get("STATION_NUMBER")
        if not station_number:
            return None

        # Parse UTC timestamp (strip tzinfo for consistent naive-UTC storage)
        datetime_utc = None
        if props.get("DATETIME"):
            try:
                dt = datetime.fromisoformat(
                    props["DATETIME"].replace("Z", "+00:00")
                )
                datetime_utc = dt.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        return NormalizedReading(
            station_number=station_number,
            data_source=self.name,
            datetime_utc=datetime_utc,
            water_level=props.get("LEVEL"),
            discharge=props.get("DISCHARGE"),
            level_symbol=props.get("LEVEL_SYMBOL_EN"),
            discharge_symbol=props.get("DISCHARGE_SYMBOL_EN"),
        )

    # ── Historical Daily Means ──────────────────────────────────────

    async def fetch_historical_daily_means(
        self,
        station_number: str,
        start_date: datetime,
        end_date: datetime,
        client=None,
    ) -> list[NormalizedDailyMean]:
        """
        Fetch historical daily mean flow/level for a single station
        over the given date range. Paginates at ECCC's limit.

        If client is provided, reuses it for connection pooling.
        """
        all_means: list[NormalizedDailyMean] = []

        datetime_filter = (
            f"{start_date.strftime('%Y-%m-%d')}/"
            f"{end_date.strftime('%Y-%m-%d')}"
        )

        async def _fetch(http_client):
            offset = 0
            while True:
                params = {
                    "STATION_NUMBER": station_number,
                    "datetime": datetime_filter,
                    "limit": 10000,  # ECCC max per request
                    "offset": offset,
                    "f": "json",
                }

                try:
                    resp = await http_client.get(
                        settings.eccc_daily_mean_url, params=params
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    logger.error(
                        f"ECCC historical {station_number} "
                        f"offset={offset}: {type(e).__name__}: {e}"
                    )
                    break

                features = data.get("features", [])
                if not features:
                    break

                for feature in features:
                    daily_mean = self._parse_daily_mean_feature(
                        feature, station_number
                    )
                    if daily_mean:
                        all_means.append(daily_mean)

                if len(features) < 10000:
                    break
                offset += 10000

        if client:
            await _fetch(client)
        else:
            async with httpx.AsyncClient(
                timeout=settings.ECCC_REQUEST_TIMEOUT
            ) as new_client:
                await _fetch(new_client)

        logger.info(
            f"ECCC: {station_number} — {len(all_means)} historical records"
        )
        return all_means

    def _parse_daily_mean_feature(
        self, feature: dict, station_number: str
    ) -> NormalizedDailyMean | None:
        """Parse a single GeoJSON feature into a NormalizedDailyMean."""
        props = feature.get("properties", {})

        date_str = props.get("DATE")
        if not date_str:
            return None

        try:
            # ECCC DATE can be "YYYY-MM-DD" or ISO with timezone
            date = datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            )
            date = date.replace(tzinfo=None)  # Naive UTC
        except (ValueError, TypeError):
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return None

        month_day = date.strftime("%m-%d")
        year = date.year

        # ECCC daily mean uses DISCHARGE and LEVEL (not DAILY_MEAN_*)
        mean_flow = props.get("DISCHARGE")
        mean_level = props.get("LEVEL")

        # Skip records with no data
        if mean_flow is None and mean_level is None:
            return None

        return NormalizedDailyMean(
            station_number=station_number,
            data_source=self.name,
            date=date,
            month_day=month_day,
            year=year,
            mean_flow=mean_flow,
            mean_level=mean_level,
        )
