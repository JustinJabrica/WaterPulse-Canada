"""
Alberta Provider
=================
Fetches hydrometric and meteorological data from Alberta's provincial
API at rivers.alberta.ca. Supplementary source for ~556 stations
that ECCC does not cover, and enriches 374 shared stations with
fields ECCC lacks (station type, basin, precipitation, reservoir data).

Endpoints used:
    - ListStationsAndAlerts    — station metadata (triple-encoded JSON)
    - WaterlevelRecords        — current readings (POST per station)
    - CSV downloads            — historical daily data (per station)

Response format: triple-encoded JSON for stations, custom JSON for
readings, CSV for historical. Each layer must be parsed separately.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

# Prevents concurrent fetch_stations() race in _get_station_datasets()
_station_cache_lock = asyncio.Lock()

from app.config import settings
from app.services.providers.base_provider import (
    BaseProvider,
    NormalizedStation,
    NormalizedReading,
    NormalizedDailyMean,
)

logger = logging.getLogger(__name__)

# Number of header rows to skip in Alberta CSV files
CSV_HEADER_ROWS = 22


class AlbertaProvider(BaseProvider):
    """Alberta provincial API — supplementary data source."""

    def __init__(self):
        # Cache for station list — avoids re-fetching from the API
        # on every call to _get_station_datasets() during historical sync.
        self._station_cache: list[NormalizedStation] | None = None

    @property
    def name(self) -> str:
        return "alberta"

    # ── Stations ────────────────────────────────────────────────────

    async def fetch_stations(self) -> list[NormalizedStation]:
        """
        Fetch all stations from rivers.alberta.ca.
        Response is triple-encoded JSON:
            outer JSON → "stations" key (string) → parse → list
        """
        async with httpx.AsyncClient(
            timeout=settings.ALBERTA_REQUEST_TIMEOUT
        ) as client:
            try:
                resp = await client.get(settings.alberta_stations_url)
                resp.raise_for_status()
                raw = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.error(f"Alberta stations fetch failed: {e}")
                return []

        # Layer 1: outer JSON has a "stations" key containing a JSON string
        stations_json = raw.get("stations")
        if not stations_json:
            logger.error("Alberta: missing 'stations' key in response")
            return []

        # Layer 2: parse the JSON string
        try:
            stations_data = json.loads(stations_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Alberta: failed to parse stations JSON: {e}")
            return []

        # Layer 3: extract the station list
        entries = stations_data.get("WISKI_ABRivers_station_parameters", [])
        if not entries:
            logger.error(
                "Alberta: missing 'WISKI_ABRivers_station_parameters' key"
            )
            return []

        stations: list[NormalizedStation] = []
        for entry in entries:
            station = self._parse_station_entry(entry)
            if station:
                stations.append(station)

        logger.info(f"Alberta: fetched {len(stations)} stations")
        return stations

    def _parse_station_entry(
        self, entry: dict
    ) -> NormalizedStation | None:
        """Parse a single Alberta station entry into a NormalizedStation."""
        station_number = entry.get("station_number")
        station_name = entry.get("station_name")
        if not station_number or not station_name:
            return None

        # Parse coordinates (may be strings)
        latitude = self._to_float(entry.get("station_latitude"))
        longitude = self._to_float(entry.get("station_longitude"))

        # Derive drainage basin prefix from station number
        drainage_prefix = (
            station_number[:2] if len(station_number) >= 2 else None
        )

        # Parse boolean-like fields
        has_capacity = entry.get("hasCapacity")
        if isinstance(has_capacity, str):
            has_capacity = has_capacity.lower() in ("true", "1", "yes")

        # Build extra dict with Alberta-internal fetch data
        extra = {}

        # TSIDs for data retrieval
        for key in ("TSID", "PCT25", "PCT75", "SECRIVER"):
            val = entry.get(key)
            if val and val != "null":
                extra[key.lower()] = val

        # Live storage and pct full TSIDs
        for key in ("liveStorage", "pctFull"):
            val = entry.get(key)
            if val and val != "null":
                extra[key] = val

        # Precipitation values (current snapshot — also stored in extra
        # so readings can reference them)
        for key in (
            "ptValueLast6h", "ptValueLast12h",
            "ptValueLast24h", "ptValueLast48h",
        ):
            val = entry.get(key)
            if val and val != "null":
                extra[key] = val

        # Dataset URLs for historical CSV downloads
        datasets = entry.get("datasets")
        if datasets:
            extra["datasets"] = datasets

        # WMO reports flag
        wmo = entry.get("WMOReports")
        if wmo:
            extra["wmo_reports"] = wmo

        return NormalizedStation(
            station_number=station_number,
            station_name=station_name,
            data_source=self.name,
            latitude=latitude,
            longitude=longitude,
            province="AB",
            station_type=self._clean_string(entry.get("station_type")),
            data_type=self._clean_string(entry.get("data_type")),
            basin_number=self._clean_string(entry.get("basin_number")),
            catchment_number=self._clean_string(
                entry.get("catchment_number")
            ),
            drainage_basin_prefix=drainage_prefix,
            real_time=True,  # Alberta stations assumed real-time
            has_capacity=has_capacity or False,
            parameter_data_status=self._clean_string(
                entry.get("parameter_data_status")
            ),
            extra=extra if extra else None,
        )

    # ── Readings ────────────────────────────────────────────────────

    async def fetch_latest_readings(
        self,
        station_numbers: list[str] | None = None,
        province: str | None = None,
    ) -> list[NormalizedReading]:
        """
        Fetch current readings for Alberta stations by POSTing
        to WaterlevelRecords per station in parallel batches.

        Filters:
            station_numbers — fetch only these specific stations
            province — ignored (Alberta is always AB)
        """
        # Province filter: Alberta only serves AB stations
        if province and province.upper() != "AB":
            return []

        # Get station list (cached on the provider instance)
        if self._station_cache is None:
            self._station_cache = await self.fetch_stations()
        if not self._station_cache:
            return []

        # Only fetch readings for water stations (R and L)
        water_stations = [
            s for s in self._station_cache
            if s.station_type in ("R", "L")
        ]

        # Filter to specific stations if requested
        if station_numbers:
            requested = set(station_numbers)
            water_stations = [
                s for s in water_stations
                if s.station_number in requested
            ]

        if not water_stations:
            return []

        readings: list[NormalizedReading] = []
        semaphore = asyncio.Semaphore(settings.ALBERTA_BATCH_SIZE)

        async with httpx.AsyncClient(
            timeout=settings.ALBERTA_REQUEST_TIMEOUT
        ) as client:
            tasks = [
                self._fetch_single_reading(client, semaphore, station)
                for station in water_stations
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for station, result in zip(water_stations, results):
            if isinstance(result, NormalizedReading):
                readings.append(result)
            elif isinstance(result, Exception):
                logger.debug(
                    f"Alberta reading {station.station_number}: {result}"
                )

        logger.info(
            f"Alberta: {len(readings)}/{len(water_stations)} "
            f"stations with readings"
        )
        return readings

    async def _fetch_single_reading(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        station: NormalizedStation,
    ) -> NormalizedReading | None:
        """Fetch current data for one Alberta station."""
        async with semaphore:
            try:
                resp = await client.post(
                    settings.alberta_readings_url,
                    data={
                        "stationNumber": station.station_number,
                        "stationType": station.station_type or "R",
                        "dataType": station.data_type or "HG",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException):
                return None

        return self._parse_reading_response(raw, station)

    def _parse_reading_response(
        self,
        raw_json,
        station: NormalizedStation,
    ) -> NormalizedReading | None:
        """Parse Alberta WaterlevelRecords response into a NormalizedReading."""
        if isinstance(raw_json, str):
            try:
                raw_json = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return None

        if not raw_json or not isinstance(raw_json, list) or len(raw_json) == 0:
            return None

        entry = raw_json[0]
        data_rows = entry.get("data", [])
        if not data_rows:
            return None

        # Find the last row with non-null values
        newest = None
        for row in reversed(data_rows):
            if len(row) > 1 and row[1] is not None:
                newest = row
                break
        if not newest:
            return None

        columns = entry.get("columnarray", [])
        units = entry.get("ts_unitsymbols", [])

        # Parse timestamp — Alberta API returns Mountain Time (MST/MDT).
        # Convert to naive UTC for consistent storage.
        reading_ts = None
        if newest[0]:
            try:
                mountain = ZoneInfo("America/Edmonton")
                local_dt = datetime.strptime(
                    newest[0], "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=mountain)
                reading_ts = local_dt.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                pass

        # Build a column-value map
        col_values = {}
        for i, col_name in enumerate(columns):
            if i == 0:
                continue  # Skip timestamp column
            key = col_name.lower().replace(" ", "_").replace("%", "pct")
            col_values[key] = newest[i] if i < len(newest) else None

        # Build extra dict with precipitation and any other provider-specific data
        extra = {}
        if station.extra:
            for precip_key, extra_key in (
                ("ptValueLast6h", "precip_last_6h"),
                ("ptValueLast12h", "precip_last_12h"),
                ("ptValueLast24h", "precip_last_24h"),
                ("ptValueLast48h", "precip_last_48h"),
            ):
                val = station.extra.get(precip_key)
                if val is not None:
                    extra[extra_key] = self._to_float(val)

        # Include units in extra for the frontend
        for i, col_name in enumerate(columns):
            if i == 0:
                continue
            key = col_name.lower().replace(" ", "_").replace("%", "pct")
            unit_key = f"{key}_unit"
            unit_val = units[i - 1] if (i - 1) < len(units) else None
            if unit_val:
                extra[unit_key] = unit_val

        return NormalizedReading(
            station_number=station.station_number,
            data_source=self.name,
            datetime_utc=reading_ts,
            water_level=self._to_float(col_values.get("level")),
            discharge=self._to_float(col_values.get("flow")),
            outflow=self._to_float(col_values.get("outflow")),
            capacity=self._to_float(col_values.get("capacity")),
            pct_full=self._to_float(col_values.get("pct_full")),
            extra=extra if extra else None,
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
        Download historical CSV for a station and compute daily means.
        Uses the dataset_location URLs embedded in the station's extra data.

        Note: start_date/end_date are used for filtering the parsed CSV
        results — the CSV itself contains ~365 days of data.

        If client is provided, reuses it for connection pooling.
        """
        all_means: list[NormalizedDailyMean] = []

        # We need the station's extra data to find CSV URLs.
        # If called standalone, fetch station list to find datasets.
        datasets = await self._get_station_datasets(station_number)
        if not datasets:
            return []

        async def _fetch(http_client):
            for data_key, keyword in [
                ("flow", "flow"),
                ("level", "water level"),
            ]:
                url = self._find_dataset_url(datasets, keyword)
                if not url:
                    continue

                # Retry up to 3 times on transient network errors
                text = None
                for attempt in range(3):
                    try:
                        resp = await http_client.get(url)
                        resp.raise_for_status()
                        text = resp.text
                        break
                    except (httpx.HTTPError, httpx.TimeoutException) as e:
                        retryable = isinstance(e, (httpx.ConnectError, httpx.ReadError))
                        if retryable and attempt < 2:
                            await asyncio.sleep(1 * (attempt + 1))
                            continue
                        logger.warning(
                            f"Alberta historical {station_number} "
                            f"{data_key}: {type(e).__name__}: {e}"
                        )
                        break
                if text is None:
                    continue

                daily_means = self._parse_csv_to_daily_means(
                    text, station_number, data_key, start_date, end_date
                )
                all_means.extend(daily_means)

        if client:
            await _fetch(client)
        else:
            async with httpx.AsyncClient(
                timeout=settings.ALBERTA_REQUEST_TIMEOUT
            ) as new_client:
                await _fetch(new_client)

        logger.info(
            f"Alberta: {station_number} — "
            f"{len(all_means)} historical records"
        )
        return all_means

    async def _get_station_datasets(
        self, station_number: str
    ) -> list[dict] | None:
        """Get dataset URLs for a station. Caches the station list with a lock."""
        async with _station_cache_lock:
            if self._station_cache is None:
                self._station_cache = await self.fetch_stations()
        for station in self._station_cache:
            if station.station_number == station_number and station.extra:
                return station.extra.get("datasets")
        return None

    def _find_dataset_url(
        self, datasets: list[dict], keyword: str
    ) -> str | None:
        """Find a CSV dataset URL by keyword in its description."""
        for ds in datasets:
            desc = ds.get("dataset_description", "").lower()
            loc = ds.get("dataset_location", "")
            if keyword.lower() in desc and loc.endswith(".csv"):
                return loc
        return None

    def _parse_csv_to_daily_means(
        self,
        text: str,
        station_number: str,
        data_key: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[NormalizedDailyMean]:
        """
        Parse an Alberta historical CSV into NormalizedDailyMean objects.
        Computes daily means from sub-daily readings, filtered by date range.
        """
        lines = text.splitlines()
        data_lines = lines[CSV_HEADER_ROWS:]
        if not data_lines:
            return []

        # Group readings by (year, month_day) and compute means
        daily_readings: dict[tuple[int, str], list[float]] = defaultdict(list)

        for line in data_lines:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                date_str = parts[0].strip()
                value_str = parts[2].strip()
                if not date_str or not value_str:
                    continue
                date = datetime.strptime(date_str, "%Y-%m-%d")

                # Filter by date range
                if date < start_date or date > end_date:
                    continue

                value = float(value_str)
                year = date.year
                month_day = date.strftime("%m-%d")
                daily_readings[(year, month_day)].append(value)
            except (ValueError, IndexError):
                continue

        # Build normalized daily means
        means: list[NormalizedDailyMean] = []
        for (year, month_day), values in daily_readings.items():
            mean_value = round(sum(values) / len(values), 4)

            mean = NormalizedDailyMean(
                station_number=station_number,
                data_source=self.name,
                date=datetime.strptime(
                    f"{year}-{month_day}", "%Y-%m-%d"
                ),
                month_day=month_day,
                year=year,
                mean_flow=mean_value if data_key == "flow" else None,
                mean_level=mean_value if data_key == "level" else None,
            )
            means.append(mean)

        return means

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _to_float(value) -> float | None:
        """Safely convert a value to float, returning None on failure."""
        if value is None or value == "null" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_string(value) -> str | None:
        """Clean a string value, converting 'null' to None."""
        if value is None or value == "null" or value == "":
            return None
        return str(value).strip()
