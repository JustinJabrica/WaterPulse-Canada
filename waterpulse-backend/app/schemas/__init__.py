from datetime import datetime
from pydantic import BaseModel, EmailStr


# ── Station Schemas ──────────────────────────────────────────────────


class StationBase(BaseModel):
    station_number: str
    station_name: str
    latitude: float | None = None
    longitude: float | None = None
    province: str | None = None
    station_type: str | None = None
    data_type: str | None = None
    data_source: str | None = None
    basin_number: str | None = None
    catchment_number: str | None = None
    drainage_basin_prefix: str | None = None
    has_capacity: bool = False


class StationResponse(StationBase):
    status: str | None = None
    real_time: bool | None = None
    drainage_area_gross: float | None = None
    drainage_area_effect: float | None = None
    contributor: str | None = None
    vertical_datum: str | None = None
    rhbn: bool | None = None
    parameter_data_status: str | None = None
    extra: dict | None = None

    model_config = {"from_attributes": True}


class StationSummary(BaseModel):
    """Lightweight station info for list views."""
    station_number: str
    station_name: str
    latitude: float | None = None
    longitude: float | None = None
    province: str | None = None
    station_type: str | None = None
    data_type: str | None = None
    data_source: str | None = None
    basin_number: str | None = None
    catchment_number: str | None = None
    drainage_basin_prefix: str | None = None
    has_capacity: bool = False

    model_config = {"from_attributes": True}


# ── Reading Schemas ──────────────────────────────────────────────────


class PercentileData(BaseModel):
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    sample_size: int


class CurrentWeather(BaseModel):
    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    humidity_pct: float | None = None
    precipitation_mm: float | None = None
    weather_code: int | None = None
    weather_description: str | None = None
    visibility_m: float | None = None
    wind_speed_kmh: float | None = None
    wind_gusts_kmh: float | None = None
    wind_direction_deg: float | None = None
    uv_index: float | None = None
    is_day: bool | None = None
    sunrise: str | None = None
    sunset: str | None = None
    time: str | None = None


class DailyForecast(BaseModel):
    date: str
    weather_code: int | None = None
    weather_description: str | None = None
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None
    apparent_temperature_max_c: float | None = None
    apparent_temperature_min_c: float | None = None
    precipitation_sum_mm: float | None = None
    precipitation_probability_pct: float | None = None
    wind_speed_max_kmh: float | None = None
    wind_gusts_max_kmh: float | None = None
    sunrise: str | None = None
    sunset: str | None = None
    uv_index_max: float | None = None
    visibility_mean_m: float | None = None


class AirQuality(BaseModel):
    us_aqi: int | None = None
    pm2_5: float | None = None
    pm10: float | None = None
    time: str | None = None


class WeatherData(BaseModel):
    current: CurrentWeather | None = None
    daily_forecast: list[DailyForecast] | None = None
    air_quality: AirQuality | None = None
    elevation_m: float | None = None


class StationWeatherResponse(BaseModel):
    station_number: str
    weather: WeatherData | None = None
    weather_fetched_at: datetime | None = None


class CurrentReadingResponse(BaseModel):
    station_number: str
    datetime_utc: datetime | None = None
    fetched_at: datetime
    data_source: str | None = None

    water_level: float | None = None
    discharge: float | None = None
    level_symbol: str | None = None
    discharge_symbol: str | None = None

    outflow: float | None = None
    capacity: float | None = None
    pct_full: float | None = None

    flow_rating: str | None = None
    level_rating: str | None = None
    pct_full_rating: str | None = None
    flow_percentiles: PercentileData | None = None
    level_percentiles: PercentileData | None = None

    extra: dict | None = None

    model_config = {"from_attributes": True}


class StationWithReading(StationSummary):
    """Station info combined with its latest reading."""
    latest_reading: CurrentReadingResponse | None = None


# ── Basin / Group Schemas ────────────────────────────────────────────


class StationGroup(BaseModel):
    prefix: str
    basin_number: str
    station_count: int
    sample_names: list[str]


class BasinInfo(BaseModel):
    basin_number: str
    total_stations: int
    group_count: int
    groups: list[StationGroup]


class ProvinceInfo(BaseModel):
    """Province with station counts and type breakdown."""
    province_code: str
    total_stations: int
    river_count: int = 0
    lake_count: int = 0
    met_count: int = 0
    river_with_reading: int = 0
    lake_with_reading: int = 0


# ── User Schemas ─────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ── Favorite Schemas ─────────────────────────────────────────────────


class FavoriteCreate(BaseModel):
    station_number: str


class FavoriteResponse(BaseModel):
    id: int
    station_number: str
    station_name: str
    added_at: datetime

    model_config = {"from_attributes": True}
