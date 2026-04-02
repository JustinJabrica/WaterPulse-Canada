# WaterPulse Backend

FastAPI with Python 3.12, async SQLAlchemy, and PostgreSQL.

## Commands
- `uvicorn app.main:app --reload` — dev server on port 8000
- `pip install -r requirements.txt` — install dependencies (use `--break-system-packages` if not in venv)
- Interactive API docs at `http://localhost:8000/docs`

## Architecture
```
app/
├── main.py              # FastAPI app, lifespan, scheduler startup
├── config.py            # All settings, URLs, paths, tuning constants
├── database.py          # Async SQLAlchemy engine and session
├── auth.py              # JWT creation, password hashing, auth dependencies
├── scheduler.py         # APScheduler (readings refresh on interval)
├── models/
│   ├── station.py       # stations table
│   ├── reading.py       # current_readings table
│   ├── historical.py    # historical_daily_means table
│   ├── weather.py       # station_weather cache table
│   ├── user.py          # users table
│   └── favorite.py      # favorite_stations table
├── schemas/
│   └── __init__.py      # Pydantic request/response models
├── routes/
│   ├── stations.py      # GET /api/stations/*
│   ├── readings.py      # GET /api/readings/*
│   ├── auth.py          # /api/auth/* (login, register, logout, me)
│   ├── favorites.py     # /api/favorites CRUD
│   └── admin.py         # /api/admin/sync-*, status
└── services/
    ├── providers/
    │   ├── __init__.py          # Provider registry (list of active providers)
    │   ├── base_provider.py     # Abstract base class and normalized dataclasses
    │   ├── eccc_provider.py     # ECCC OGC API (api.weather.gc.ca) — all of Canada
    │   └── alberta_provider.py  # Alberta provincial API (rivers.alberta.ca) — supplementary
    ├── station_sync.py          # Orchestrator: loops providers, merges, upserts
    ├── readings_refresh.py      # Orchestrator: loops providers, deduplicates, computes ratings
    ├── historical_sync.py       # Orchestrator: loops providers, builds percentile table
    ├── weather.py               # Open-Meteo forecast + AQI fetch functions
    ├── weather_cache.py         # On-demand weather: check cache, fetch if stale, upsert
    └── ratings.py               # Percentile computation (shared by all providers)
```

## Provider Architecture

Data is fetched through a provider/adapter pattern. Each provider knows how to talk to one external API and returns data in a normalized format. Orchestrator services (`station_sync`, `readings_refresh`, `historical_sync`) loop through all registered providers, merge results, then run shared logic (ratings, DB writes). Weather is fetched on demand per station, not during bulk refresh.

### Base provider interface (`base_provider.py`)

Every provider implements:
- `fetch_stations() → list[NormalizedStation]`
- `fetch_latest_readings() → list[NormalizedReading]`
- `fetch_historical_daily_means(station_number, start, end) → list[NormalizedDailyMean]`

Each normalized dataclass includes a `data_source` field.

### ECCC provider (`eccc_provider.py`)

Primary source for all of Canada. Fetches from `api.weather.gc.ca` OGC API:
- Stations: `hydrometric-stations/items` — paginated, filterable by province
- Readings: `hydrometric-realtime/items` — province-by-province with datetime window, deduplicated to latest per station
- Historical: `hydrometric-daily-mean/items` — per station with date range
- Response format: standard GeoJSON FeatureCollection (no special decoding)
- Provides: coordinates, drainage area, status, contributor, vertical datum, RHBN flag
- Does NOT provide: station type (R/L/M), basin/catchment, reservoir capacity, precipitation

### Alberta provider (`alberta_provider.py`)

Supplementary source for ~92 provincial-only water stations and ~464 met stations that ECCC does not cover. Also enriches the 374 shared stations with fields ECCC lacks.
- Stations: `ListStationsAndAlerts` — response is triple-encoded JSON (outer JSON → `stations` string → parse → `WISKI_ABRivers_station_parameters` list)
- Readings: POST to `WaterlevelRecords` — per station, batched at `settings.ALBERTA_BATCH_SIZE`
- Historical: 365-day CSV downloads via `dataset_location` URLs in each station's `datasets` array
- Provides: station type, basin, catchment, data type, reservoir capacity (hasCapacity/pctFull/liveStorage), precipitation totals (ptValueLast6h/12h/24h/48h), data staleness status
- Does NOT provide: drainage area, active/discontinued status, contributor, RHBN flag

### Merge strategy

Providers run in order: **Alberta first, ECCC second**. For the 374 stations that exist in both APIs:
- Alberta fields take priority (station_type, basin, catchment, reservoir data, precipitation, station name)
- ECCC fills in fields Alberta doesn't have (drainage area, status, contributor, vertical datum, RHBN)
- Coordinates and station numbers are identical across sources (<1m difference)
- Readings deduplication: keyed by station_number, first write wins (Alberta's readings include precipitation context)

### Adding new providers

To add a new provincial data source (BC, SK, etc.):
1. Create `app/services/providers/{province}_provider.py` implementing `BaseProvider`
2. Add one line to `providers/__init__.py`
3. No changes needed to orchestrators, routes, or shared logic

## Data Sources

### Station coverage (Alberta)

| Category | Alberta API | ECCC API | Shared | Alberta-only |
|---|---|---|---|---|
| River (R) | 364 | ~380 | 303 | 61 |
| Lake/Reservoir (L) | 102 | ~109 | 68 | 31 |
| Meteorological (M) | 498 | 0 | 3 | 464 |
| **Total** | **930** | **489 active** | **374** | **556** |

ECCC covers 79.6% of Alberta's water stations. The remaining 20.4% are irrigation infrastructure, dam outflows, and provincial monitoring sites available only through rivers.alberta.ca.

### Station coverage (all of Canada)

ECCC provides ~2,700 active hydrometric stations across 13 provinces and territories, with ~2,100 reporting real-time data. Plus 121 active Alberta stations not in the provincial API.

## Database Tables

### `stations`
Station metadata from all sources. Nullable fields accommodate stations that exist in only one API.

- `station_number` (PK) — WSC format (e.g. 05AA004) or provincial format
- `station_name` — mixed case from Alberta; ALL CAPS from ECCC
- `station_type` — R (river), L (lake/reservoir), M (meteorological). From Alberta directly; inferred from name for ECCC-only
- `latitude`, `longitude`
- `province` — 2-letter code (AB, BC, ON, etc.)
- `data_source` — `eccc`, `alberta`, or `both`
- `status` — Active / Discontinued (from ECCC; nullable)
- `real_time` — boolean (from ECCC; assumed true for Alberta)
- `basin_number` — Alberta basin code (OLD, BOW, RED, etc.; nullable for non-AB)
- `catchment_number` — Alberta sub-basin (05AA, 05AB, etc.; nullable for non-AB)
- `drainage_basin_prefix` — first 2 digits of station_number (national grouping)
- `drainage_area_gross` — km² (from ECCC; nullable)
- `drainage_area_effect` — km² (from ECCC; nullable)
- `contributor` — operating agency (from ECCC; nullable)
- `vertical_datum` — reference datum (from ECCC; nullable)
- `rhbn` — boolean, Reference Hydrometric Basin Network (from ECCC; nullable)
- `has_capacity` — boolean, reservoir tracking (from Alberta; nullable)
- `data_type` — HG (water) or PC (precipitation) (from Alberta; nullable)

### `current_readings`
Latest readings with ratings and source tracking.

- `station_number` (FK)
- `water_level` — metres (from ECCC `LEVEL` or Alberta reading)
- `discharge` — m³/s (from ECCC `DISCHARGE` or Alberta reading)
- `datetime_utc` — reading timestamp in UTC
- `datetime_local` — reading timestamp with local timezone offset
- `fetched_at` — when our backend fetched it
- `data_source` — which provider supplied this reading
- `level_symbol` — data quality flag (from ECCC; nullable)
- `discharge_symbol` — data quality flag (from ECCC; nullable)
- `precip_last_6h`, `precip_last_12h`, `precip_last_24h`, `precip_last_48h` — mm (from Alberta; nullable)
- Rating and percentile fields (computed by us)
- `weather` — JSON column (deprecated, no longer populated; weather is now in `station_weather` table)

### `station_weather`
Cached weather data per station, fetched on demand from Open-Meteo.

- `station_number` (FK, unique)
- `weather_data` — JSON blob: `{current, daily_forecast, air_quality, elevation_m}`
- `weather_fetched_at` — naive UTC timestamp of last fetch

### `historical_daily_means`
Daily mean flow/level keyed by MM-DD for percentile calculations.

- `station_number` (FK)
- `month_day` — MM-DD format
- `mean_flow`, `mean_level`
- `data_source` — which provider supplied this data
- `year_count` — how many years contributed to this mean

### `users` and `favorite_stations`
Unchanged. Favourites reference `station_number`.

## API Endpoints

### Stations
- `GET /api/stations/` — list all (filterable by `province`, `station_type`, `basin`, `catchment`)
- `GET /api/stations/provinces` — all provinces with station counts
- `GET /api/stations/basins` — Alberta basins with station groups and counts
- `GET /api/stations/{station_number}` — single station detail
- `GET /api/stations/{station_number}/current` — station with latest reading and rating
- `GET /api/stations/{station_number}/weather` — cached weather (fetches from Open-Meteo if stale >30 min)
- `GET /api/stations/nearby?lat=X&lon=Y&radius=50` — proximity search
- `GET /api/stations/search?q=bow+river&province=AB` — text search on station name (optional `province` filter)

### Readings
- `POST /api/readings/refresh` — on-demand readings refresh (filterable by `station_numbers`, `province`)
- `GET /api/readings/last-updated` — timestamp of most recent refresh
- `GET /api/readings/all` — all current readings (filterable by `province`, `station_type`)
- `GET /api/readings/by-province/{province_code}` — current readings for a province
- `GET /api/readings/by-basin/{basin_number}` — current readings for an Alberta basin
- `GET /api/readings/by-catchment/{catchment}` — current readings for an Alberta catchment
- `GET /api/readings/by-drainage-basin/{prefix}` — readings by national drainage basin (05, 07, 08...)

### Auth (HTTPOnly Cookie Model)
- `POST /api/auth/register` — create account, set session cookie
- `POST /api/auth/login` — validate credentials, set HTTPOnly `access_token` cookie + plain `csrf_token` cookie
- `POST /api/auth/logout` — clear both cookies
- `GET /api/auth/me` — read JWT from cookie, return user object (or 401)

### Favourites (auth required)
- `GET /api/favorites/` — list user's favourites
- `POST /api/favorites/` — add a station
- `DELETE /api/favorites/{station_number}` — remove a station

### Admin
- `POST /api/admin/sync-stations` — run station sync across all providers
- `POST /api/admin/sync-historical` — run historical sync across all providers
- `POST /api/admin/refresh-readings` — full readings refresh (filterable by `province`)
- `GET /api/admin/status` — station counts by province/source, reading counts, last updated, historical stats

## Background Services

### Orchestrator services (call providers)
- `station_sync.py` — loops all providers, merges with Alberta priority, upserts to `stations` table. Run frequency: twice per year or on demand.
- `readings_refresh.py` — loops all providers, deduplicates by station_number (first write wins), computes ratings against historical percentiles, and upserts (not delete-all). Weather is NOT fetched here — it's fetched on demand per station. Supports selective refresh by `station_numbers` or `province`. Run frequency: on demand via frontend (`POST /api/readings/refresh`) or admin endpoint.
- `historical_sync.py` — loops all providers, fetches daily means, computes MM-DD aggregates for percentile table. Run frequency: quarterly (when HYDAT updates) or on demand. Initial sync for all of Canada is a long background job.

### Shared services (source-agnostic)
- `weather.py` — Open-Meteo forecast + air quality APIs with retry/backoff on 429. No API key needed.
- `weather_cache.py` — On-demand weather: checks `station_weather` table, returns cached data if fresh (< `WEATHER_CACHE_TTL_MINUTES`), otherwise fetches for a single station and caches. Called by `GET /api/stations/{id}/weather`.
- `ratings.py` — percentile computation using ±7 day window across up to 5 years of historical data. Minimum 5 values required.

## Rating Methodology
- Flow/level: current value compared against historical percentiles (±`PERCENTILE_WINDOW_DAYS` day window across up to `HISTORICAL_LOOKBACK_YEARS` years)
- P10 boundaries: Very Low < P10 ≤ Low < P25 ≤ Average ≤ P75 < High ≤ P90 < Very High
- Reservoir fullness: fixed scale (Very Low <20%, Low 20-39%, Average 40-70%, High 71-90%, Very High >90%)
- Minimum `MIN_HISTORICAL_VALUES` historical values required to compute percentiles

## Environment Variables (.env)

### Required
- `DATABASE_URL` — async connection string (postgresql+asyncpg://...)
- `DATABASE_URL_SYNC` — sync connection string for Alembic (postgresql+psycopg2://...)
- `SECRET_KEY` — JWT signing key

### Data sources (defaults provided in config.py)
- `ECCC_BASE_URL` — default `https://api.weather.gc.ca`
- `ECCC_DATAMART_BASE_URL` — default `https://dd.weather.gc.ca/today/hydrometric`
- `ALBERTA_BASE_URL` — default `https://rivers.alberta.ca`
- `OPEN_METEO_FORECAST_URL` — default `https://api.open-meteo.com/v1/forecast`
- `OPEN_METEO_AQI_URL` — default `https://air-quality-api.open-meteo.com/v1/air-quality`

### Other (defaults provided in config.py)
- `FRONTEND_URL` — default `http://localhost:3000`
- `ALGORITHM` — default `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default `1440`
- `ECCC_REALTIME_WINDOW_HOURS` — default `6` (hours of readings to fetch from ECCC)
- `READINGS_STALE_MINUTES` — default `3` (skip re-fetching stations refreshed within this window)
- `WEATHER_CACHE_TTL_MINUTES` — default `30` (serve cached weather if younger than this)
- `WEATHER_BATCH_SIZE` — default `40` (coordinates per Open-Meteo request)
- `WEATHER_BATCH_DELAY` — default `1.5` (seconds between Open-Meteo batches)
- `WEATHER_MAX_RETRIES` — default `3` (retry attempts on 429 rate-limit)

All API paths, URL templates, tuning constants (page sizes, batch sizes, timeouts, historical lookback), and the provinces list are defined in `config.py` with sensible defaults. See `config.py` for the full reference.

## Rules
- NEVER commit `.env` files
- All external URLs go through `config.py` — never hardcode URLs in provider or service files
- Use Canadian English in user-facing strings: favourites, colours, metres
- All water data is provisional — include disclaimers where appropriate
- Alberta API responses are triple-encoded JSON — always parse layer by layer with error handling
- ECCC API responses are standard GeoJSON — coordinates are `[longitude, latitude]` (not lat/lon)
- Provider files handle only fetch + parse — shared logic (ratings, DB) lives in orchestrators, weather is fetched on demand via `weather_cache.py`
- New data sources = new provider file + one line in registry — never modify orchestrator code to add a source
- All timestamps stored as naive UTC — providers must convert local times to UTC before returning (Alberta uses `ZoneInfo("America/Edmonton")` for MST/MDT conversion). `fetched_at` uses `datetime.now(timezone.utc).replace(tzinfo=None)`.
