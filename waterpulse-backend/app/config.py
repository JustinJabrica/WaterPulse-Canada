"""
WaterPulse Backend Configuration
=================================
Single source of truth for all URLs, paths, and tuning parameters.

Deployment-specific values (database, auth, URLs) come from .env — no defaults.
Implementation constants (API paths, batch sizes, timeouts) have defaults here.

Usage in any service file:
    from app.config import settings
    url = f"{settings.ECCC_BASE_URL}{settings.ECCC_STATIONS_PATH}"
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    All configuration loaded from .env with defaults where appropriate.
    Grouped by concern so it's easy to find what you need.
    """

    # ── From .env (required, no defaults) ──────────────────────────

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    FRONTEND_URL: str
    ECCC_BASE_URL: str
    ECCC_DATAMART_BASE_URL: str
    ALBERTA_BASE_URL: str
    OPEN_METEO_FORECAST_URL: str
    OPEN_METEO_AQI_URL: str
    READINGS_REFRESH_INTERVAL_MINUTES: int = 10

    # Cookie Secure flag — True on HTTPS production, False on local HTTP
    COOKIE_SECURE: bool = False

    # ── ECCC — Collection paths (constants) ────────────────────────
    # Appended to ECCC_BASE_URL. Listed here so you can see every
    # endpoint the app uses in one place.
    ECCC_STATIONS_PATH: str = "/collections/hydrometric-stations/items"
    ECCC_REALTIME_PATH: str = "/collections/hydrometric-realtime/items"
    ECCC_DAILY_MEAN_PATH: str = "/collections/hydrometric-daily-mean/items"
    ECCC_MONTHLY_MEAN_PATH: str = "/collections/hydrometric-monthly-mean/items"
    ECCC_ANNUAL_STATS_PATH: str = "/collections/hydrometric-annual-statistics/items"
    ECCC_ANNUAL_PEAKS_PATH: str = "/collections/hydrometric-annual-peaks/items"

    # ── Alberta — Endpoint paths (constants) ───────────────────────
    ALBERTA_STATIONS_PATH: str = "/DataService/ListStationsAndAlerts"
    ALBERTA_CSV_BASE_PATH: str = "/apps/Basins/data/porExtracts"
    ALBERTA_JSON_BASE_PATH: str = "/apps/Basins/data/figures/river/abrivers/stationdata"

    # Alberta — CSV download URL templates
    # Use .format(station=station_number) to build the full URL
    ALBERTA_CSV_FLOW_TEMPLATE: str = (
        "/apps/Basins/data/porExtracts/"
        "porExtract_AB_{station}_Q_Cmd.Merged-NRT.Public.csv"
    )
    ALBERTA_CSV_LEVEL_TEMPLATE: str = (
        "/apps/Basins/data/porExtracts/"
        "porExtract_AB_{station}_HG_Cmd.RelAbs.Cor-Datum.C.Public.csv"
    )
    ALBERTA_JSON_READING_TEMPLATE: str = (
        "/apps/Basins/data/figures/river/abrivers/stationdata/"
        "{type}_{param}_{station}_table.json"
    )

    # ── Tuning — Pagination and batch sizes ────────────────────────
    ECCC_PAGE_SIZE: int = 500           # Items per ECCC API request (max 10,000)
    ALBERTA_BATCH_SIZE: int = 50        # Concurrent Alberta readings requests
    WEATHER_BATCH_SIZE: int = 40        # Coordinates per Open-Meteo request
    WEATHER_BATCH_DELAY: float = 1.5    # Seconds between Open-Meteo batches
    WEATHER_MAX_RETRIES: int = 3        # Retry attempts on 429 rate-limit
    WEATHER_CACHE_TTL_MINUTES: int = 30 # Serve cached weather if younger than this
    ECCC_REALTIME_WINDOW_HOURS: int = 6 # Hours of readings to fetch from ECCC
    READINGS_STALE_MINUTES: int = 3     # Skip stations refreshed within this window

    # ── Tuning — Historical data and ratings ───────────────────────
    HISTORICAL_LOOKBACK_YEARS: int = 5  # Years of daily means for percentiles
    PERCENTILE_WINDOW_DAYS: int = 7     # ±days around current date for comparison
    MIN_HISTORICAL_VALUES: int = 5      # Minimum data points to compute percentiles

    # ── Tuning — Timeouts (seconds) ───────────────────────────────
    ECCC_REQUEST_TIMEOUT: int = 60
    ALBERTA_REQUEST_TIMEOUT: int = 60
    WEATHER_REQUEST_TIMEOUT: int = 30

    # Historical fetches return up to 10K records; needs more time than real-time
    HISTORICAL_REQUEST_TIMEOUT: int = 180

    # ── Provinces and territories ──────────────────────────────────
    # Used by ECCC provider to loop through all regions
    PROVINCES: list[str] = [
        "AB", "BC", "SK", "MB", "ON", "QC",
        "NB", "NS", "PE", "NL", "YT", "NT", "NU",
    ]

    # ── Convenience methods — build full URLs ──────────────────────

    @property
    def eccc_stations_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_STATIONS_PATH}"

    @property
    def eccc_realtime_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_REALTIME_PATH}"

    @property
    def eccc_daily_mean_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_DAILY_MEAN_PATH}"

    @property
    def eccc_monthly_mean_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_MONTHLY_MEAN_PATH}"

    @property
    def eccc_annual_stats_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_ANNUAL_STATS_PATH}"

    @property
    def eccc_annual_peaks_url(self) -> str:
        return f"{self.ECCC_BASE_URL}{self.ECCC_ANNUAL_PEAKS_PATH}"

    @property
    def alberta_stations_url(self) -> str:
        return f"{self.ALBERTA_BASE_URL}{self.ALBERTA_STATIONS_PATH}"

    def alberta_csv_flow_url(self, station: str) -> str:
        path = self.ALBERTA_CSV_FLOW_TEMPLATE.format(station=station)
        return f"{self.ALBERTA_BASE_URL}{path}"

    def alberta_csv_level_url(self, station: str) -> str:
        path = self.ALBERTA_CSV_LEVEL_TEMPLATE.format(station=station)
        return f"{self.ALBERTA_BASE_URL}{path}"

    def alberta_json_reading_url(
        self, station: str, station_type: str = "R", param: str = "HG"
    ) -> str:
        path = self.ALBERTA_JSON_READING_TEMPLATE.format(
            type=station_type, param=param, station=station
        )
        return f"{self.ALBERTA_BASE_URL}{path}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Module-level shortcut — import this in service files
settings = get_settings()
