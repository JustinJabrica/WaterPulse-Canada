"""
Base Provider Interface
========================
Abstract base class that every data provider must implement.
Providers fetch from external APIs and return normalized dataclasses.
Orchestrators (station_sync, readings_refresh, historical_sync) consume
these normalized objects — they never touch raw API responses.

Each dataclass includes a `data_source` field so orchestrators know
which provider produced each record.

Designed for scalability: core fields cover the universal data model,
while `extra` dicts let each provider carry source-specific data
(precipitation intervals, reservoir metrics, internal fetch IDs)
without requiring changes to the base interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ── Normalized Dataclasses ──────────────────────────────────────────


@dataclass
class NormalizedStation:
    """
    Station metadata from any provider. All fields beyond station_number,
    station_name, and data_source are optional to accommodate providers
    that only supply a subset of fields.
    """
    station_number: str
    station_name: str
    data_source: str                          # "eccc", "alberta", "bc", etc.

    # Location
    latitude: float | None = None
    longitude: float | None = None
    province: str | None = None               # 2-letter code (AB, BC, ON...)

    # Classification
    station_type: str | None = None           # R (river), L (lake), M (met)
    data_type: str | None = None              # HG (water), PC (precipitation)

    # Grouping — used by provincial providers for regional organization
    basin_number: str | None = None           # Regional basin code
    catchment_number: str | None = None       # Sub-basin identifier
    drainage_basin_prefix: str | None = None  # First 2 digits of station_number

    # Federal fields (from ECCC; nullable for provincial-only stations)
    status: str | None = None                 # Active / Discontinued
    real_time: bool | None = None             # Reporting real-time data
    drainage_area_gross: float | None = None  # km²
    drainage_area_effect: float | None = None # km²
    contributor: str | None = None            # Operating agency
    vertical_datum: str | None = None         # Reference datum
    rhbn: bool | None = None                  # Reference Hydrometric Basin Network

    # Reservoir tracking — any provider can supply these
    has_capacity: bool | None = None          # Whether reservoir data is available

    # Data quality/staleness — any provider can supply
    parameter_data_status: str | None = None  # Current data reporting status

    # Provider-specific metadata — each provider can stash internal
    # fetch data here (TSIDs, dataset URLs, API keys, etc.) without
    # polluting the shared interface. Orchestrators pass this through
    # to the DB as JSON.
    extra: dict | None = None


@dataclass
class NormalizedReading:
    """
    A single current reading from any provider. Includes the raw
    measurement values. Ratings and weather are NOT included — those
    are computed by the orchestrator after all providers have been merged.
    """
    station_number: str
    data_source: str                          # "eccc", "alberta", "bc", etc.

    # Timestamp in UTC (frontend converts to local)
    datetime_utc: datetime | None = None

    # Core measurements — universal across all providers
    water_level: float | None = None          # metres
    discharge: float | None = None            # m³/s

    # Quality symbols (from ECCC; other providers may also supply)
    level_symbol: str | None = None           # Estimated, ice-affected, etc.
    discharge_symbol: str | None = None

    # Reservoir measurements — any provider with reservoir data
    outflow: float | None = None              # m³/s
    capacity: float | None = None             # m³ or %
    pct_full: float | None = None             # Reservoir fullness %

    # Provider-specific measurements — precipitation windows, snow
    # water equivalent, water temperature, tidal levels, etc.
    # Keys are provider-defined (e.g. "precip_last_6h", "snow_depth_cm").
    # Orchestrators store this as JSON on the reading record.
    extra: dict | None = None


@dataclass
class NormalizedDailyMean:
    """
    One day's mean flow or level for a station. Used to build the
    historical percentile table (keyed by MM-DD).
    """
    station_number: str
    data_source: str                          # "eccc", "alberta", "bc", etc.

    date: datetime                            # Full date of this daily mean
    month_day: str                            # MM-DD format (e.g. "03-19")
    year: int                                 # Year this mean is from

    mean_flow: float | None = None            # m³/s
    mean_level: float | None = None           # metres


# ── Abstract Base Class ─────────────────────────────────────────────


class BaseProvider(ABC):
    """
    Interface contract for all data providers.

    Each provider knows how to talk to one external API and returns
    data in the normalized format above. Providers handle ONLY fetch
    and parse — all shared logic (ratings, weather, DB writes) lives
    in the orchestrator services.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'eccc', 'alberta')."""
        ...

    @abstractmethod
    async def fetch_stations(self) -> list[NormalizedStation]:
        """
        Fetch all station metadata from this provider's API.
        Returns normalized station objects ready for the orchestrator
        to merge and upsert.
        """
        ...

    @abstractmethod
    async def fetch_latest_readings(
        self,
        station_numbers: list[str] | None = None,
        province: str | None = None,
    ) -> list[NormalizedReading]:
        """
        Fetch the most recent reading for active stations from this
        provider's API. Returns normalized readings ready for
        deduplication and rating computation by the orchestrator.

        Optional filters (providers should honour these when possible):
            station_numbers — fetch only these specific stations
            province — fetch only stations in this province
        When both are None, fetches all stations.
        """
        ...

    @abstractmethod
    async def fetch_historical_daily_means(
        self,
        station_number: str,
        start_date: datetime,
        end_date: datetime,
        client=None,
    ) -> list[NormalizedDailyMean]:
        """
        Fetch historical daily mean flow/level for a single station
        over the given date range. Returns normalized daily means
        ready for percentile table construction by the orchestrator.

        If client (httpx.AsyncClient) is provided, reuse it for
        connection pooling. Otherwise create a new one per call.
        """
        ...
