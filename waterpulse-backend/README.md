# WaterPulse Backend

Real-time river, lake, and reservoir conditions for anyone visiting Canada's waterways. Built with FastAPI, async SQLAlchemy, and PostgreSQL.

The backend fetches data from multiple government APIs (ECCC federal + Alberta provincial), merges it with Alberta-priority logic, computes percentile-based ratings against historical norms, and serves it all through a REST API. Weather and air quality are fetched on demand per station (not during bulk refresh) and cached for 30 minutes.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Technology Stack](#technology-stack)
3. [How FastAPI Works](#how-fastapi-works)
4. [Project Structure](#project-structure)
5. [Configuration and Environment Variables](#configuration-and-environment-variables)
6. [SQLAlchemy and the Database](#sqlalchemy-and-the-database)
7. [Alembic — Database Migrations](#alembic--database-migrations)
8. [Pydantic — Validation and Schemas](#pydantic--validation-and-schemas)
9. [The Provider Architecture](#the-provider-architecture)
10. [How External APIs Are Called (httpx)](#how-external-apis-are-called-httpx)
11. [The Data Pipeline](#the-data-pipeline)
12. [Authentication and Security](#authentication-and-security)
13. [Background Scheduling](#background-scheduling)
14. [API Endpoints](#api-endpoints)
15. [Data Sources](#data-sources)
16. [Station Numbering System](#station-numbering-system)
17. [Database Schema](#database-schema)
18. [Weather and Air Quality Detail](#weather-and-air-quality-detail)
19. [Rating Methodology](#rating-methodology)
20. [Architecture Decisions](#architecture-decisions)
21. [Gotchas and Lessons Learned](#gotchas-and-lessons-learned)
22. [Testing Strategies](#testing-strategies)
23. [Common Tasks](#common-tasks)
24. [Data Disclaimer](#data-disclaimer)

---

## Getting Started

### Prerequisites

- **Python 3.12** (3.13 also works; 3.14 is not yet supported due to missing pre-built wheels for pydantic-core)
- **PostgreSQL** installed and running locally
- **Node.js** (for the Next.js frontend, covered separately)

### 1. Create the Database

```bash
# Using psql from the command line
psql -U postgres -c "CREATE DATABASE waterpulse_db;"
```

If using pgAdmin, right-click "Databases" → "Create" → "Database" and name it `waterpulse_db`.

### 2. Set Up the Backend

```bash
cd waterpulse-backend
```

Create and activate a virtual environment using Python 3.12:

```bash
# Windows
py -3.12 -m venv venv
venv\Scripts\activate

# macOS / Linux
python3.12 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` and configure:

```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/waterpulse_db
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:your_password@localhost:5432/waterpulse_db
SECRET_KEY=change-this-to-a-random-secret-key
```

Generate a secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`

See [Configuration and Environment Variables](#configuration-and-environment-variables) for the full variable reference.

### 4. Run Migrations and Start the Server

```bash
# Apply database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive API docs are at `http://localhost:8000/docs`.

### 5. Populate the Database

The database starts empty. Populate it by calling the admin endpoints in this order:

```bash
# Step 1 — Sync stations (~8,500 stations from all providers, takes ~15 seconds)
curl -X POST http://localhost:8000/api/admin/sync-stations

# Step 2 — Sync historical data (daily means for percentile calculations, takes hours for all of Canada)
curl -X POST http://localhost:8000/api/admin/sync-historical

# Step 3 — Refresh current readings (latest data + ratings, takes ~30 seconds)
curl -X POST http://localhost:8000/api/admin/refresh-readings
```

Or use the interactive docs at `http://localhost:8000/docs` to trigger these.

### 6. Verify Everything

```bash
curl http://localhost:8000/api/admin/status
```

Returns station counts by province and source, reading counts, last updated timestamp, and historical data statistics.

### Getting Started with Docker (Alternative)

If you prefer Docker over local setup, you can skip steps 1-4 above:

1. **Copy the environment template** at the repo root:
   ```bash
   cp .env.example .env
   ```
2. **Fill in secrets** — at minimum, set `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env`
3. **Start all services** from the repo root:
   ```bash
   docker-compose up --build
   ```
   This starts PostgreSQL, runs Alembic migrations automatically, and launches the backend on port 8000.
4. **Sync stations and data** — same as steps 4-5 above (use curl or the docs UI at http://localhost:8000/docs)

> In Docker, the backend source code is bind-mounted, so code changes are picked up automatically via uvicorn's `--reload` flag. You do not need to restart the container after editing Python files.

---

## Technology Stack

| Package | What It Does | Where It's Used |
|---|---|---|
| **FastAPI** | Web framework for building REST APIs. Built on top of Starlette and Pydantic. Handles routing, request/response, dependency injection, and auto-generates API documentation. | `main.py`, all route files |
| **Starlette** | The underlying ASGI framework that FastAPI is built on. Handles HTTP protocol, middleware, CORS, and request/response objects. You rarely import it directly — FastAPI wraps it. | `main.py` (middleware) |
| **Pydantic** | Data validation library. Defines the shape of request/response data using Python type hints. FastAPI uses it automatically for request parsing and response serialization. | `schemas/__init__.py`, `config.py` |
| **pydantic-settings** | Extension of Pydantic for loading configuration from `.env` files. | `config.py` |
| **SQLAlchemy** | Database toolkit and ORM (Object-Relational Mapper). Maps Python classes to database tables and lets you query using Python instead of raw SQL. | `database.py`, all model files, all service files |
| **asyncpg** | PostgreSQL driver for async Python. SQLAlchemy uses this under the hood for async database connections. You never call it directly. | Referenced in `DATABASE_URL` |
| **psycopg2** | PostgreSQL driver for synchronous Python. Used only by Alembic for migrations (Alembic doesn't support async). | Referenced in `DATABASE_URL_SYNC` |
| **Alembic** | Database migration tool. Tracks schema changes (add/remove/rename columns) and applies them incrementally. Works with SQLAlchemy models. | `alembic/` directory |
| **httpx** | Async HTTP client library (similar to `requests` but supports `async`/`await`). Used to call external APIs (ECCC, Alberta, Open-Meteo). | All provider files, `weather.py` |
| **APScheduler** | Background task scheduler. Runs readings refresh every 10 minutes and historical sync annually on Jan 1st, without needing a separate process like Celery. | `scheduler.py` |
| **python-jose** | JWT (JSON Web Token) library for creating and verifying authentication tokens. | `auth.py` |
| **bcrypt** | Password hashing library. Securely stores passwords so even if the database is compromised, passwords can't be read. | `auth.py` |
| **slowapi** | Rate limiting for FastAPI endpoints. Per-IP limits using in-memory storage (swap to Redis for multi-replica AWS deployments). | `limiter.py`, route decorators |
| **uvicorn** | ASGI server that actually runs the FastAPI application. It's what listens on port 8000 and passes HTTP requests to FastAPI. | Command line |

### How These Fit Together

```
Browser/Frontend
       │
       ▼
   uvicorn (ASGI server, port 8000)
       │
       ▼
   Starlette (HTTP handling, middleware, CORS)
       │
       ▼
   FastAPI (routing, dependency injection, validation)
       │
       ├── Pydantic (validates request data, shapes response data)
       │
       ├── SQLAlchemy + asyncpg (reads/writes PostgreSQL)
       │
       └── httpx (calls external APIs: ECCC, Alberta, Open-Meteo)
```

---

## How FastAPI Works

### The Basics

FastAPI is a Python web framework that lets you define API endpoints as regular Python functions. It uses type hints to automatically validate incoming data and generate documentation.

```python
# This is a complete API endpoint:
@router.get("/api/stations/{station_number}")
async def get_station(station_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Station).where(Station.station_number == station_number)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station
```

Here's what each part does:

- **`@router.get("/api/stations/{station_number}")`** — Registers this function to handle GET requests at this URL. `{station_number}` is a path parameter.
- **`async def`** — The function is asynchronous (can use `await` to wait for database queries without blocking other requests).
- **`station_number: str`** — FastAPI automatically extracts this from the URL path and validates it's a string.
- **`db: AsyncSession = Depends(get_db)`** — Dependency injection (explained below).
- **`raise HTTPException`** — Returns an HTTP error response (404 in this case).
- **`return station`** — FastAPI automatically converts the SQLAlchemy model to JSON using Pydantic.

### Dependency Injection

FastAPI's `Depends()` is a way to automatically provide things that a route function needs. Instead of creating a database connection inside every route, you declare it as a dependency:

```python
# This function creates a database session and cleans it up after:
async def get_db():
    async with async_session() as session:
        try:
            yield session        # <-- the route uses this session
        finally:
            await session.close()  # <-- cleanup happens automatically

# Any route that needs a database session just declares it:
async def my_route(db: AsyncSession = Depends(get_db)):
    # db is ready to use here
    # when the route returns, get_db's finally block runs
```

This pattern is used for:
- **Database sessions** — `Depends(get_db)` provides an `AsyncSession`
- **Authentication** — `Depends(get_current_user)` reads the cookie and returns the user
- **Authorization** — `Depends(require_user)` rejects unauthenticated requests

Dependencies can depend on other dependencies. For example, `require_user` depends on `get_current_user`, which depends on `get_db`:

```python
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    # ... decode token, query database, return user

async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

### Routers

Instead of putting all routes in one file, FastAPI lets you organize them using `APIRouter`:

```python
# In routes/stations.py:
router = APIRouter(prefix="/api/stations", tags=["stations"])

@router.get("/")          # Becomes GET /api/stations/
@router.get("/{station_number}")  # Becomes GET /api/stations/05AA004

# In main.py — register the router:
app.include_router(stations.router)
```

### Middleware

Middleware intercepts every request before it reaches a route and/or every response before it's sent back. WaterPulse uses two middleware layers:

1. **CORS Middleware** (from Starlette) — Allows the Next.js frontend at `localhost:3000` to make requests to the API at `localhost:8000`. Without this, browsers block cross-origin requests.

2. **CSRF Middleware** (custom) — Protects against cross-site request forgery by requiring that POST/PUT/DELETE requests include an `X-CSRF-Token` header that matches the `csrf_token` cookie.

### Lifespan Events

The `lifespan` context manager in `main.py` runs code when the app starts up and shuts down:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP — runs once when the server starts
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Create tables if they don't exist
    start_scheduler()                                    # Start scheduled jobs (readings + historical)

    yield  # <-- the app runs here, handling requests

    # SHUTDOWN — runs when the server stops
    stop_scheduler()
```

### Auto-Generated Documentation

FastAPI automatically creates interactive API docs at `http://localhost:8000/docs` (Swagger UI). Every route, its parameters, request body shape, and response shape are documented based on your type hints and Pydantic models. You don't need to write this documentation — it comes from the code itself.

---

## Project Structure

```
waterpulse-backend/
├── app/
│   ├── main.py                  # Application entry point, middleware, lifespan
│   ├── config.py                # All configuration (loaded from .env)
│   ├── database.py              # Database engine (pool_pre_ping, pool_recycle), session factory, Base class
│   ├── auth.py                  # JWT, password hashing, cookie management
│   ├── limiter.py               # Rate limiting (slowapi, in-memory; swap to Redis for AWS)
│   ├── scheduler.py             # APScheduler (readings every 10 min, historical Jan 1st)
│   │
│   ├── models/                  # SQLAlchemy models (one class = one table)
│   │   ├── __init__.py          # Re-exports all models
│   │   ├── station.py           # stations table
│   │   ├── reading.py           # current_readings table
│   │   ├── historical.py        # historical_daily_means table
│   │   ├── user.py              # users table
│   │   └── favorite.py          # favorite_stations table
│   │
│   ├── schemas/                 # Pydantic models (request/response shapes)
│   │   └── __init__.py          # All schemas in one file
│   │
│   ├── routes/                  # API endpoint handlers
│   │   ├── stations.py          # GET /api/stations/*
│   │   ├── readings.py          # GET /api/readings/*
│   │   ├── auth.py              # POST /api/auth/*
│   │   ├── favorites.py         # /api/favorites/*
│   │   └── admin.py             # /api/admin/* (sync triggers, status)
│   │
│   └── services/                # Business logic
│       ├── providers/           # External API adapters
│       │   ├── __init__.py      # Provider registry
│       │   ├── base_provider.py # Abstract interface + dataclasses
│       │   ├── eccc_provider.py # ECCC federal API
│       │   └── alberta_provider.py  # Alberta provincial API
│       │
│       ├── station_sync.py      # Orchestrator: merge + upsert stations
│       ├── readings_refresh.py  # Orchestrator: merge + rate + store readings
│       ├── historical_sync.py   # Orchestrator: fetch + store daily means
│       ├── weather.py           # Open-Meteo weather + AQI fetch functions
│       └── weather_cache.py     # On-demand weather: cache check, fetch if stale, upsert
│
├── alembic/                     # Database migration files
│   ├── env.py                   # Alembic configuration
│   └── versions/                # Migration scripts (one per schema change)
│
├── alembic.ini                  # Alembic settings
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (never committed)
└── .env.example                 # Template showing what .env needs
```

### What Goes Where

| You Want To... | Edit This |
|---|---|
| Add a new database column | `models/*.py`, then create an Alembic migration |
| Add a new API endpoint | `routes/*.py` |
| Change what a response looks like | `schemas/__init__.py` |
| Add a new data source (e.g. BC) | `services/providers/bc_provider.py` + one line in `providers/__init__.py` |
| Change how stations are merged | `services/station_sync.py` |
| Change how ratings work | `services/readings_refresh.py` |
| Add a new configuration variable | `config.py` + `.env` |
| Change the refresh interval | `.env` (`READINGS_REFRESH_INTERVAL_MINUTES`) |

---

## Configuration and Environment Variables

### How It Works

Configuration is managed by `pydantic-settings`, which reads from the `.env` file and validates the values using Python type hints.

**`.env` file** — Contains deployment-specific values (database URL, secret key, API base URLs). This file is never committed to version control because it contains secrets.

**`config.py`** — Defines the `Settings` class that loads from `.env`. It also defines implementation constants (API paths, batch sizes, timeouts) with sensible defaults.

```python
class Settings(BaseSettings):
    # Required — must be in .env (no default = app crashes if missing)
    DATABASE_URL: str
    SECRET_KEY: str

    # Has a default — can be overridden in .env if needed
    ECCC_PAGE_SIZE: int = 500
    PROVINCES: list[str] = ["AB", "BC", "SK", ...]

    class Config:
        env_file = ".env"          # Read from this file
        case_sensitive = True      # DATABASE_URL != database_url
```

### Why Two Database URLs?

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/waterpulse
DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@localhost:5432/waterpulse
```

These point to the **same database** but use different drivers:
- **`asyncpg`** — Async driver used by the running application (FastAPI is async)
- **`psycopg2`** — Sync driver used by Alembic (Alembic doesn't support async)

### Full Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | Async connection string (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Yes | — | Sync connection string for Alembic (`postgresql+psycopg2://...`) |
| `SECRET_KEY` | Yes | — | JWT signing key. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | Login token lifetime (1440 = 24 hours) |
| `FRONTEND_URL` | No | `http://localhost:3000` | CORS allowed origin |
| `ECCC_BASE_URL` | No | `https://api.weather.gc.ca` | ECCC federal API base |
| `ECCC_DATAMART_BASE_URL` | No | `https://dd.weather.gc.ca/today/hydrometric` | ECCC datamart base |
| `ALBERTA_BASE_URL` | No | `https://rivers.alberta.ca` | Alberta provincial API base |
| `OPEN_METEO_FORECAST_URL` | No | `https://api.open-meteo.com/v1/forecast` | Weather API |
| `OPEN_METEO_AQI_URL` | No | `https://air-quality-api.open-meteo.com/v1/air-quality` | Air quality API |
| `READINGS_REFRESH_INTERVAL_MINUTES` | No | `10` | Auto-refresh frequency |
| `WEATHER_CACHE_TTL_MINUTES` | No | `30` | How long cached weather is considered fresh before re-fetching |
| `WEATHER_BATCH_SIZE` | No | `40` | Max coordinates per Open-Meteo request |
| `WEATHER_BATCH_DELAY` | No | `1.5` | Seconds to wait between weather batches (rate limit protection) |
| `WEATHER_MAX_RETRIES` | No | `3` | Retry attempts on Open-Meteo 429 responses (exponential backoff) |

**Connection string format:**

```
postgresql+asyncpg://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

If your password contains special characters like `@` or `/`, URL-encode them (e.g., `p@ss` becomes `p%40ss`).

### Accessing Settings in Code

```python
from app.config import settings

url = settings.ECCC_BASE_URL  # "https://api.weather.gc.ca"
page_size = settings.ECCC_PAGE_SIZE  # 500
```

The `settings` object is created once (cached with `@lru_cache`) and shared across the entire application.

### Convenience URL Properties

Instead of assembling URLs manually, `config.py` has properties that combine base URLs with paths:

```python
# Instead of:
url = f"{settings.ECCC_BASE_URL}/collections/hydrometric-stations/items"

# Use:
url = settings.eccc_stations_url  # Same result, but the path is defined in one place
```

This means if an API path changes, you only update `config.py`, not every provider file.

---

## SQLAlchemy and the Database

### What SQLAlchemy Does

SQLAlchemy is an ORM — it maps Python classes to database tables. Instead of writing SQL, you work with Python objects:

```python
# Without SQLAlchemy (raw SQL):
cursor.execute("SELECT * FROM stations WHERE station_number = '05AA004'")
row = cursor.fetchone()
name = row[1]  # hope column 1 is station_name

# With SQLAlchemy:
result = await db.execute(
    select(Station).where(Station.station_number == "05AA004")
)
station = result.scalar_one_or_none()
name = station.station_name  # typed, autocompleted by your editor
```

### How Models Work

Each model class maps to one database table. The class attributes define the columns:

```python
class Station(Base):
    __tablename__ = "stations"  # Actual table name in PostgreSQL

    # Primary key — every row has a unique station_number
    station_number: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Regular columns — Mapped[type] defines the Python type
    station_name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float | None] = mapped_column(Float)  # | None = nullable

    # JSON column — stores arbitrary Python dicts as JSON in PostgreSQL
    extra: Mapped[dict | None] = mapped_column(JSON)

    # Relationship — not a column, just tells SQLAlchemy about the FK link
    current_readings: Mapped[list["CurrentReading"]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
    )
```

Key concepts:
- **`Mapped[str]`** — This column contains a string and is NOT NULL
- **`Mapped[float | None]`** — This column contains a float and IS nullable
- **`mapped_column(String(20), primary_key=True)`** — Column details (type, constraints)
- **`relationship()`** — Tells SQLAlchemy that another table has a foreign key pointing here. Not a real column — it's a convenience for loading related objects.
- **`cascade="all, delete-orphan"`** — When a station is deleted, its readings and favourites are automatically deleted too.

### The `Base` Class

All models inherit from `Base`, which is defined in `database.py`:

```python
class Base(DeclarativeBase):
    pass
```

This class does nothing on its own. Its job is to be a common parent that SQLAlchemy uses to discover all your models and generate the database schema. When you see `Base.metadata.create_all` in `main.py`, SQLAlchemy looks at every class that inherits from `Base` and creates the corresponding tables.

### Common Query Patterns

```python
# Get one record by primary key
result = await db.execute(select(Station).where(Station.station_number == "05AA004"))
station = result.scalar_one_or_none()  # Returns Station or None

# Get multiple records with filters
result = await db.execute(
    select(Station)
    .where(Station.station_type == "R", Station.province == "AB")
    .order_by(Station.station_number)
)
stations = result.scalars().all()  # Returns list[Station]

# Count records
result = await db.execute(select(func.count()).select_from(Station))
total = result.scalar()  # Returns int

# Group by and count
result = await db.execute(
    select(Station.province, func.count())
    .group_by(Station.province)
)
by_province = {row[0]: row[1] for row in result.all()}

# Insert a new record
station = Station(station_number="05AA004", station_name="Pincher Creek")
db.add(station)
await db.commit()  # Writes to the database

# Update an existing record
station.station_name = "Pincher Creek at Pincher Creek"
db.add(station)  # Mark as changed
await db.commit()  # Writes the update

# Delete a record
await db.delete(station)
await db.commit()

# Delete all records in a table (used by readings refresh)
await db.execute(delete(CurrentReading))
await db.commit()

# Upsert (insert or update on conflict) — used by historical sync
from sqlalchemy.dialects.postgresql import insert
stmt = insert(HistoricalDailyMean).values(rows)
stmt = stmt.on_conflict_do_update(
    constraint="uq_station_key_date_year",
    set_={"value": stmt.excluded.value},
)
await db.execute(stmt)
```

### Sessions and Transactions

A **session** is a connection to the database that tracks what you've changed. Nothing is written until you call `commit()`:

```python
db.add(station)         # Queued in memory
db.add(reading)         # Also queued
await db.commit()       # NOW both are written to the database in one transaction
```

If an error happens before `commit()`, nothing is written. This is called a **transaction** — either everything succeeds or nothing does.

The `get_db()` dependency creates a session for each request and automatically closes it when the request is done.

### The `flush()` vs `commit()` Distinction

- **`flush()`** — Writes pending changes to the database but does NOT commit the transaction. Other queries in the same session can see the changes, but they'll be rolled back if the session errors out. Used when you need a row to exist for a foreign key reference before the full commit.
- **`commit()`** — Writes AND commits. Changes become permanent and visible to other sessions.

In `readings_refresh.py`, we use `flush()` after auto-creating stations so the reading inserts can reference them via foreign key, then `commit()` at the end to make everything permanent.

---

## Alembic — Database Migrations

### What Migrations Are

When you change a model (add a column, rename a field, change a type), the database doesn't update automatically. Alembic generates migration scripts that apply those changes incrementally.

Think of it like version control for your database schema — each migration is a step that transforms the database from one state to the next.

### Key Files

- **`alembic.ini`** — Configuration file. Points to the migrations directory.
- **`alembic/env.py`** — Tells Alembic where to find your models and database URL. It imports all models so Alembic can compare them against the actual database.
- **`alembic/versions/`** — Contains migration scripts, each with an `upgrade()` and `downgrade()` function.

### How `env.py` Works

```python
from app.config import settings
from app.database import Base
from app.models import Station, CurrentReading, ...  # Import ALL models

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)  # Use sync driver
target_metadata = Base.metadata  # Alembic compares this against the real database
```

This is why `DATABASE_URL_SYNC` exists — Alembic needs a synchronous connection, but the rest of the app uses async.

### Common Commands

```bash
# Generate a new migration by comparing models to the database
alembic revision --autogenerate -m "Add province column to stations"

# Apply all pending migrations
alembic upgrade head

# See current migration state
alembic current

# Roll back one migration
alembic downgrade -1

# Roll back to the beginning
alembic downgrade base

# See migration history
alembic history
```

### Autogenerate vs Manual

`--autogenerate` compares your Python models against the actual database and generates a migration script. It detects:
- New tables and columns
- Removed columns
- Type changes
- Index and constraint changes

It does NOT detect:
- Column renames (it sees a drop + add, not a rename)
- Data migrations (copying data between columns)

For renames and data migrations, you edit the generated script manually.

### What a Migration Looks Like

```python
def upgrade():
    # Add a new column
    op.add_column('stations', sa.Column('province', sa.String(2)))

    # Copy data from old column to new
    op.execute("UPDATE stations SET province = 'AB'")

    # Drop old column
    op.drop_column('stations', 'old_province_field')

def downgrade():
    # Reverse everything (so you can roll back)
    op.add_column('stations', sa.Column('old_province_field', sa.String(2)))
    op.execute("UPDATE stations SET old_province_field = province")
    op.drop_column('stations', 'province')
```

### Important: Never Skip Migrations

If you change a model and run the app without creating a migration, the app might work (because `Base.metadata.create_all` creates missing tables but doesn't alter existing ones). But the next time you run `alembic revision --autogenerate`, it will try to generate a migration for changes you already applied manually, causing confusion.

Always use Alembic for schema changes in development and production.

---

## Pydantic — Validation and Schemas

### What Pydantic Does

Pydantic validates data using Python type hints. In WaterPulse, it serves two purposes:

1. **Request validation** — Ensures incoming data has the right shape and types
2. **Response serialization** — Controls what data is sent back to the frontend

### Schemas vs Models

This is a common source of confusion:

- **SQLAlchemy models** (`models/station.py`) — Define the database table structure. Used for reading and writing the database.
- **Pydantic schemas** (`schemas/__init__.py`) — Define the API request/response structure. Used for validating input and shaping output.

They often have similar fields, but they're separate because:
- You might not want to expose every database column in the API
- You might want to combine data from multiple tables in one response
- Request data (what the user sends) has different fields than response data (what you send back)

### How Schemas Work

```python
# A schema for the API response (what the frontend receives):
class StationSummary(BaseModel):
    station_number: str
    station_name: str
    latitude: float | None = None
    province: str | None = None
    station_type: str | None = None

    model_config = {"from_attributes": True}  # Allows conversion from SQLAlchemy models
```

**`from_attributes = True`** is critical — it tells Pydantic to read values from SQLAlchemy model attributes (like `station.station_name`) instead of expecting a dictionary. Without this, `return station` in a route would fail.

### Nested Schemas

Schemas can contain other schemas:

```python
class StationWithReading(StationSummary):
    latest_reading: CurrentReadingResponse | None = None
    # Inherits all fields from StationSummary, adds latest_reading
```

FastAPI automatically serializes nested schemas to nested JSON:
```json
{
    "station_number": "05AA004",
    "station_name": "Pincher Creek at Pincher Creek - WSC",
    "latest_reading": {
        "water_level": 0.356,
        "discharge": 1.14,
        "flow_rating": "average"
    }
}
```

### Request Validation

For POST endpoints, Pydantic validates the request body:

```python
class UserCreate(BaseModel):
    email: EmailStr       # Must be a valid email format
    username: str         # Required string
    password: str         # Required string

@router.post("/register")
async def register(user_data: UserCreate, ...):
    # If the request body is missing "email" or it's not a valid email,
    # FastAPI automatically returns a 422 error with details.
    # You never need to check this manually.
    pass
```

---

## The Provider Architecture

### The Big Picture

WaterPulse fetches data from multiple government APIs. Each API has a completely different format:

- **ECCC** (Environment and Climate Change Canada) — Standard GeoJSON, paginated, one GET request per province
- **Alberta** — Triple-encoded JSON for stations, POST per station for readings, CSV for historical data

The **provider pattern** isolates this complexity. Each provider knows how to talk to one API and translates its response into a common format. The rest of the application never sees raw API responses.

```
┌─────────────────────┐     ┌─────────────────────────┐
│   ECCC API          │     │   Alberta API            │
│   (GeoJSON)         │     │   (triple-encoded JSON)  │
└────────┬────────────┘     └────────┬────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────┐     ┌─────────────────────────┐
│   ECCCProvider      │     │   AlbertaProvider        │
│   (fetch + parse)   │     │   (fetch + parse)        │
└────────┬────────────┘     └────────┬────────────────┘
         │                           │
         ▼                           ▼
    NormalizedStation           NormalizedStation
    NormalizedReading           NormalizedReading
         │                           │
         └──────────┬────────────────┘
                    ▼
         ┌──────────────────┐
         │   Orchestrator   │
         │   (merge, rate,  │
         │    write to DB)  │
         └──────────────────┘
```

### The Base Interface

Every provider must implement three methods, defined in `base_provider.py`:

```python
class BaseProvider(ABC):
    @property
    def name(self) -> str:
        """Short identifier like 'eccc' or 'alberta'"""

    async def fetch_stations(self) -> list[NormalizedStation]:
        """Fetch all station metadata from this provider's API"""

    async def fetch_latest_readings(self) -> list[NormalizedReading]:
        """Fetch the most recent reading for every active station"""

    async def fetch_historical_daily_means(
        self, station_number, start_date, end_date
    ) -> list[NormalizedDailyMean]:
        """Fetch historical daily mean flow/level for a single station"""
```

### Normalized Dataclasses

These are plain Python data containers that hold the output of each provider. They're intentionally not SQLAlchemy models — providers don't know about the database.

```python
@dataclass
class NormalizedStation:
    station_number: str          # Required — the unique ID
    station_name: str            # Required
    data_source: str             # "eccc", "alberta", etc.
    latitude: float | None       # Optional — not all providers have coordinates
    province: str | None         # Optional
    station_type: str | None     # Optional
    # ... many more optional fields ...
    extra: dict | None = None    # Provider-specific data (see below)
```

The `extra` field is an escape hatch. Each provider can stash whatever it needs here (Alberta puts precipitation values, TSIDs, and dataset URLs; ECCC doesn't use it). The orchestrator passes `extra` through to the database as JSON without interpreting it.

### The Provider Registry

```python
# providers/__init__.py
_PROVIDERS = [AlbertaProvider(), ECCCProvider()]

def get_active_providers():
    return _PROVIDERS
```

The order matters: Alberta runs first, so its data takes priority for the 374 shared stations.

### Adding a New Provider

To add British Columbia's data:

1. Create `providers/bc_provider.py` implementing `BaseProvider`
2. Add one line: `_PROVIDERS = [AlbertaProvider(), BCProvider(), ECCCProvider()]`

No changes needed to orchestrators, routes, models, or anything else.

### The Orchestrators

Orchestrators are the bridge between providers and the database. They:
1. Loop through all providers
2. Merge the results (Alberta priority)
3. Apply shared logic (ratings)
4. Write to the database

There are three orchestrators:

| File | What It Does | How Often |
|---|---|---|
| `station_sync.py` | Merges station metadata from all providers, upserts to DB | Twice per year or on demand |
| `readings_refresh.py` | Merges readings, computes percentile ratings, upserts to `current_readings` table | Every 10 minutes |
| `historical_sync.py` | Fetches daily means per station, upserts in batches of 200 rows using short-lived DB sessions | Annually (Jan 1st) or on demand |

### Merge Strategy (Alberta Priority)

Providers run in order: **Alberta first, ECCC second**. For the 374 stations that exist in both APIs:

- Alberta fields take priority (station_type, basin, catchment, reservoir data, precipitation, station name)
- ECCC fills in fields Alberta doesn't have (drainage area, status, contributor, vertical datum, RHBN)
- Coordinates and station numbers are identical across sources (<1m difference)
- Readings deduplication: keyed by station_number, first write wins (Alberta's readings include precipitation context)
- Shared stations get `data_source` set to `"both"`

---

## How External APIs Are Called (httpx)

### What httpx Is

`httpx` is Python's async HTTP client. It's like the `requests` library, but it supports `async`/`await`, which means it doesn't block the server while waiting for an API response.

### Basic Usage

```python
import httpx

async with httpx.AsyncClient(timeout=60) as client:
    # GET request
    response = await client.get(
        "https://api.weather.gc.ca/collections/hydrometric-stations/items",
        params={"PROV_TERR_STATE_LOC": "AB", "limit": 500, "f": "json"}
    )
    response.raise_for_status()  # Raises an error if HTTP status >= 400
    data = response.json()       # Parse JSON response body

    # POST request (Alberta uses POST for readings)
    response = await client.post(
        "https://rivers.alberta.ca/DataService/WaterlevelRecords",
        data={"stationNumber": "05AA004", "stationType": "R", "dataType": "HG"}
    )
```

### The `AsyncClient` Context Manager

```python
async with httpx.AsyncClient(timeout=60) as client:
    # All requests inside here share the same connection pool.
    # When the block exits, connections are cleaned up.
    response1 = await client.get(url1)
    response2 = await client.get(url2)
```

Using a context manager (`async with`) ensures connections are properly closed even if an error occurs.

### Error Handling

All providers use the same error handling pattern:

```python
try:
    resp = await client.get(url, params=params)
    resp.raise_for_status()  # Raises httpx.HTTPStatusError for 4xx/5xx
    data = resp.json()
except (httpx.HTTPError, httpx.TimeoutException) as e:
    logger.error(f"Request failed: {e}")
    return []  # Return empty data instead of crashing
```

This means a single API failure doesn't crash the whole sync — other providers and other provinces continue.

### Concurrency with Semaphores

When fetching readings for 400+ stations, we don't want to hit an API with 400 simultaneous requests. A semaphore limits concurrency:

```python
semaphore = asyncio.Semaphore(50)  # Max 50 concurrent requests

async def fetch_one(station):
    async with semaphore:  # Waits here if 50 requests are already in flight
        response = await client.post(url, data={...})
        return response.json()

# Launch all 400 at once — the semaphore ensures only 50 run at a time
tasks = [fetch_one(s) for s in stations]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### How Each API Is Called

#### ECCC (Environment and Climate Change Canada)

- **Base URL**: `https://api.weather.gc.ca`
- **Format**: Standard GeoJSON FeatureCollection
- **Auth**: None required
- **Pagination**: `limit` and `offset` parameters (max 10,000 per request)
- **Stations**: `GET /collections/hydrometric-stations/items?PROV_TERR_STATE_LOC=AB&limit=500&offset=0&f=json`
  - Looped province by province (13 provinces)
  - Returns station metadata, coordinates, drainage area, contributor
- **Real-time readings**: `GET /collections/hydrometric-realtime/items?PROV_TERR_STATE_LOC=AB&datetime=...&f=json`
  - 1-hour datetime window, province by province
  - Returns water level and/or discharge for active stations
- **Historical daily means**: `GET /collections/hydrometric-daily-mean/items?STATION_NUMBER=05BH004&datetime=2021-01-01/2026-01-01&f=json`
  - Per station, paginated at 10,000 rows
  - Returns daily mean flow (DISCHARGE) and level (LEVEL)

**Important**: ECCC GeoJSON coordinates are `[longitude, latitude]` (not lat/lon). The provider handles this swap.

#### Alberta Provincial API

- **Base URL**: `https://rivers.alberta.ca`
- **Auth**: None required
- **Stations**: `GET /DataService/ListStationsAndAlerts`
  - Single request returns all 964 stations
  - Response is **triple-encoded JSON**: outer JSON contains a `stations` key with a JSON string, which when parsed contains a `WISKI_ABRivers_station_parameters` key with the actual list
- **Readings**: `POST /DataService/WaterlevelRecords` (one per station)
  - POST body: `stationNumber`, `stationType`, `dataType`
  - Batched at 50 concurrent requests
  - Response contains a time series with the latest reading at the end
- **Historical**: CSV download per station via URLs embedded in station metadata
  - 22 header rows to skip
  - Sub-daily readings averaged to daily means by the provider

#### Open-Meteo (Weather and Air Quality)

- **Base URL**: `https://api.open-meteo.com/v1/forecast` (weather), `https://air-quality-api.open-meteo.com/v1/air-quality` (AQI)
- **Auth**: None required (free tier, ~10,000 calls/day)
- **Batching**: Up to 40 coordinates per request (comma-separated lat/lon)
- **Returns**: Current conditions, 7-day forecast, air quality index

---

## The Data Pipeline

### Station Sync (Twice per Year)

```
1. Alberta provider fetches ~964 stations from rivers.alberta.ca
2. ECCC provider fetches ~7,965 stations from api.weather.gc.ca (all 13 provinces)
3. Merge: Alberta's fields win for 374 shared stations, ECCC enriches with federal data
4. Upsert all ~8,500 stations into the database
5. Stations not in either API but with recent readings are auto-created (minimal records)
```

**Merge rules for shared stations:**
- Alberta wins: station_name (mixed case), station_type, basin_number, catchment_number, has_capacity, extra (precipitation, TSIDs)
- ECCC fills in: status (Active/Discontinued), drainage_area_gross, contributor, vertical_datum, rhbn
- `data_source` is set to `"both"`

### Readings Refresh (Every 10 Minutes)

```
1. Alberta provider POSTs to ~466 water stations, gets ~394 readings
2. ECCC provider GETs real-time data for all 13 provinces, gets ~1,350 readings
3. Merge: Alberta readings kept for shared stations (first-write wins)
4. Auto-create station records for any readings from unknown stations
5. Look up each station in the DB for coordinates and reservoir info
6. For each reading:
   a. Query historical daily means within a ±7 day window
   b. Compute percentiles (P10, P25, P50, P75, P90)
   c. Rate the current value: very low / low / average / high / very high
7. Upsert each reading (ON CONFLICT DO UPDATE on station_number) — existing readings for other stations are preserved
8. Commit to database
```

Weather is NOT fetched during the readings refresh. It is fetched on demand when a user requests `GET /api/stations/{station_number}/weather`. See [Weather and Air Quality Detail](#weather-and-air-quality-detail) for how the caching works.

### Historical Sync (Quarterly)

```
1. Query the database for all R/L stations
2. For each provider:
   a. Find stations it should handle (data_source matches)
   b. Fetch 5 years of daily mean data per station (concurrency-limited to 10)
   c. Split each NormalizedDailyMean into flow and level DB rows
   d. Upsert with ON CONFLICT UPDATE
3. Prune entries older than 5 years per station/key/date
```

---

## Authentication and Security

### How Auth Works

WaterPulse uses **HTTPOnly cookie-based authentication** instead of sending tokens in headers. This is more secure because JavaScript can't read HTTPOnly cookies, making XSS attacks less dangerous.

#### The Flow

```
1. User submits email + password
   └── Frontend POSTs to /api/auth/login

2. Backend validates credentials
   └── Hashes the password with bcrypt and compares

3. Backend creates a JWT and sets two cookies:
   ├── access_token (HTTPOnly) — the actual JWT, invisible to JavaScript
   └── csrf_token (plain cookie) — readable by JavaScript for CSRF protection

4. Frontend calls GET /api/auth/me
   └── Browser automatically sends the cookies
   └── Backend reads the JWT from the cookie, returns the user object

5. All subsequent requests include credentials: "include"
   └── Browser attaches cookies automatically — frontend never touches the JWT

6. Logout: POST /api/auth/logout
   └── Backend clears both cookies
```

#### JWT (JSON Web Token)

A JWT is a signed string that contains the user's ID and an expiry time:

```python
# Creating a token:
payload = {"sub": "42", "exp": datetime(2026, 4, 2, ...)}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
# Result: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiIs..."

# Verifying a token:
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
user_id = int(payload["sub"])  # 42
```

The `SECRET_KEY` in `.env` is what makes the signature secure. Anyone with the key can create valid tokens, so it must be kept secret.

#### CSRF Protection

Because cookies are sent automatically by the browser, a malicious site could trick a logged-in user's browser into making requests. CSRF protection prevents this:

1. On login, the backend sets a `csrf_token` cookie (readable by JS)
2. The frontend reads this cookie and includes it as an `X-CSRF-Token` header on POST/PUT/DELETE requests
3. The backend middleware checks that the header matches the cookie
4. A malicious site can trigger the browser to send the cookie, but it **can't read the cookie** to set the header (same-origin policy), so the request is blocked

#### Guest Access

Most endpoints work without authentication. The `get_current_user` dependency returns `None` for guests instead of raising an error. Only routes that use `require_user` (favourites) reject unauthenticated requests.

#### Password Validation

Registration requires a minimum of 8 characters. This is enforced on both the frontend (client-side check before submission) and the backend (returns 400 if violated). No complexity rules — length over complexity follows current NIST guidelines.

#### Rate Limiting

Per-IP rate limits are enforced using `slowapi` (`limiter.py`). In-memory storage by default — swap to Redis for multi-replica AWS deployments by changing the `storage_uri` parameter.

| Endpoint | Limit | Rationale |
|---|---|---|
| `POST /api/auth/register` | 3/hour | Prevents account spam |
| `POST /api/auth/login` | 10/minute | Prevents brute force |
| `POST /api/admin/sync-*` | 5/minute | Expensive external API calls |
| `POST /api/admin/refresh-readings` | 5/minute | Expensive external API calls |
| All other endpoints | 60/minute | General abuse prevention |

When a limit is exceeded, the API returns `429 Too Many Requests`.

---

## Background Scheduling

APScheduler runs two background jobs:

```python
# scheduler.py — readings refresh (every 10 minutes)
scheduler.add_job(
    _run_readings_refresh,
    trigger=IntervalTrigger(minutes=settings.READINGS_REFRESH_INTERVAL_MINUTES),
    id="readings_refresh",
    max_instances=1,  # Prevents overlap if a refresh takes longer than 10 minutes
)

# scheduler.py — historical sync (January 1st at 03:00 UTC)
scheduler.add_job(
    _run_historical_sync,
    trigger=CronTrigger(month=1, day=1, hour=3, minute=0),
    id="historical_sync",
    max_instances=1,
)
```

The scheduler starts when the FastAPI app starts (in the `lifespan` function) and stops when the app shuts down.

`max_instances=1` is important — if a job takes longer than expected, the scheduler won't start another instance concurrently. It waits for the current one to finish, then runs the next one.

Each job creates its own database session (not tied to any HTTP request) and catches all exceptions so a failed run doesn't kill the scheduler.

Station sync is NOT scheduled — it's triggered manually via the admin endpoint because it's infrequent (twice per year) and the station list rarely changes. Historical sync and readings refresh can also be triggered manually via admin endpoints in addition to their scheduled runs.

---

## API Endpoints

### Stations

| Method | Path | Description |
|---|---|---|
| GET | `/api/stations/` | List all stations (filterable by `station_type`, `basin`, `catchment`, `province`) |
| GET | `/api/stations/provinces` | List all provinces with R/L station counts (meteorological excluded) |
| GET | `/api/stations/basins` | List Alberta basins with station groups and counts |
| GET | `/api/stations/search?q=bow+river&province=AB` | Search R/L stations by name (case-insensitive partial match, optional `province` filter, default limit 100) |
| GET | `/api/stations/nearby?lat=X&lon=Y&radius=50` | Find stations within a radius in kilometres (configurable `radius` and `limit`) |
| GET | `/api/stations/bbox?min_lat=X&max_lat=X&min_lon=X&max_lon=X` | Bounding box search for map viewport — R/L only, returns StationWithReading, limit 500 (max 1000), optional `province` and `station_type` filters |
| GET | `/api/stations/{station_number}` | Full detail for one station |
| GET | `/api/stations/{station_number}/current` | Station with its latest reading and rating |
| GET | `/api/stations/{station_number}/weather` | Cached weather and AQI (fetches from Open-Meteo if stale >30 min) |

### Readings

| Method | Path | Description |
|---|---|---|
| POST | `/api/readings/refresh` | On-demand readings refresh (filterable by `station_numbers`, `province`) |
| GET | `/api/readings/last-updated` | Timestamp of most recent data refresh |
| GET | `/api/readings/all` | All current readings (filterable by `station_type`, `province`) |
| GET | `/api/readings/by-province/{province_code}` | Current readings for all R/L stations in a province |
| GET | `/api/readings/by-basin/{basin_number}` | Current readings for an Alberta basin |
| GET | `/api/readings/by-catchment/{catchment}` | Current readings for an Alberta catchment |
| GET | `/api/readings/by-drainage-basin/{prefix}` | Readings by national drainage basin prefix (05, 07, 08...) |

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account, set session cookies |
| POST | `/api/auth/login` | Validate credentials, set HTTPOnly `access_token` cookie + plain `csrf_token` cookie |
| POST | `/api/auth/logout` | Clear both cookies |
| GET | `/api/auth/me` | Return current user from cookie (or 401) |

### Favourites (Auth Required)

| Method | Path | Description |
|---|---|---|
| GET | `/api/favorites/` | List user's favourite stations |
| POST | `/api/favorites/` | Add a station to favourites |
| DELETE | `/api/favorites/{station_number}` | Remove from favourites |

### Admin

| Method | Path | Description | Frequency |
|---|---|---|---|
| POST | `/api/admin/sync-stations` | Run station sync across all providers | Twice per year or on demand |
| POST | `/api/admin/sync-historical` | Run historical sync for all of Canada (can take hours; in K8s, use the CronJob instead) | Annually (Jan 1st auto) or on demand |
| POST | `/api/admin/refresh-readings` | Manual readings refresh | On demand (auto every 10 min) |
| GET | `/api/admin/status` | Station counts by province/source, reading counts, historical stats | Any time |

---

## Data Sources

### Station Coverage (Alberta)

| Category | Alberta API | ECCC API | Shared | Alberta-only |
|---|---|---|---|---|
| River (R) | 364 | ~380 | 303 | 61 |
| Lake/Reservoir (L) | 102 | ~109 | 68 | 31 |
| Meteorological (M) | 498 | 0 | 3 | 464 |
| **Total** | **930** | **489 active** | **374** | **556** |

ECCC covers 79.6% of Alberta's water stations. The remaining 20.4% are irrigation infrastructure, dam outflows, and provincial monitoring sites available only through rivers.alberta.ca.

### Station Coverage (All of Canada)

ECCC provides ~7,800 total hydrometric stations across 13 provinces and territories, with ~2,700 active and ~2,100 reporting real-time data. Combined with Alberta's provincial stations, the system serves approximately 8,500 total stations.

### Weather and Air Quality

Weather and air quality data are sourced from Open-Meteo, a free and open-source API that does not require an API key.

**Current conditions:** temperature, apparent temperature, humidity, precipitation, weather code, visibility, wind speed/gusts/direction, UV index, sunrise/sunset.

**7-day daily forecast:** temperature ranges, precipitation sum and probability, wind speeds, sunrise/sunset, UV index, visibility, weather code.

**Air quality:** US AQI, PM2.5, PM10. Especially important for Alberta, where wildfire smoke seasons can push AQI above 200.

Weather and air quality are fetched on demand per station via `GET /api/stations/{station_number}/weather`. Results are cached in the `station_weather` table for 30 minutes (`WEATHER_CACHE_TTL_MINUTES`). When a user views a station, the endpoint checks the cache first; if the cached data is fresh (less than 30 minutes old), it is returned immediately without calling Open-Meteo. Otherwise, the backend fetches fresh data for that single station, caches it, and returns it. Both weather and AQI APIs accept arrays of coordinates, batched at 40 per request (`WEATHER_BATCH_SIZE`).

---

## Station Numbering System

Canadian hydrometric station numbers follow the Water Survey of Canada (WSC) format. Understanding the format helps make sense of the data model and grouping logic.

### Format: `DDSSNNNN`

```
05BH004
││││└── 004  — Sequential station number within the sub-basin
│││└─── H    — Sub-basin letter (A-Z within the basin)
││└──── B    — Basin letter (A-Z within the drainage area)
└└───── 05   — Major drainage basin number
```

### Major Drainage Basins

The first two digits identify one of Canada's major drainage basins:

| Prefix | Drainage Basin | Flows To |
|---|---|---|
| 01 | Maritime Provinces | Atlantic Ocean |
| 02 | St. Lawrence | Atlantic Ocean |
| 03 | Northern Quebec & Labrador | Atlantic Ocean |
| 04 | Southwest Hudson Bay | Hudson Bay |
| 05 | Saskatchewan / Nelson | Hudson Bay |
| 06 | Western Hudson Bay | Hudson Bay |
| 07 | Arctic — Great Slave Lake | Arctic Ocean |
| 08 | Pacific | Pacific Ocean |
| 09 | Yukon | Pacific Ocean / Bering Sea |
| 10 | Arctic — Arctic Coast | Arctic Ocean |
| 11 | Mississippi | Gulf of Mexico |

Most Alberta stations start with `05` (Saskatchewan/Nelson basin — includes the Bow, Oldman, Red Deer, North Saskatchewan, and South Saskatchewan rivers) or `07` (Athabasca, Peace, and Hay rivers flowing north to the Arctic).

### How This Relates to the Code

- **`drainage_basin_prefix`** on the Station model stores the first 2 digits — used by the `/api/readings/by-drainage-basin/{prefix}` endpoint for national grouping
- **`catchment_number`** stores the first 4 characters (e.g., `05BH`) — Alberta's sub-basin grouping, used by the `/api/readings/by-catchment/{catchment}` endpoint
- **`basin_number`** is Alberta's own basin naming scheme (BOW, OLD, RED, etc.) — separate from the WSC numbering but mapped to the same geographic areas

---

## Database Schema

The application uses five tables:

### `stations`

Station metadata from all sources. Nullable fields accommodate stations that exist in only one API.

| Column | Type | Description |
|---|---|---|
| `station_number` | String (PK) | WSC format (e.g. 05AA004) or provincial format |
| `station_name` | String | Mixed case from Alberta; ALL CAPS from ECCC |
| `station_type` | String | R (river), L (lake/reservoir), M (meteorological) |
| `latitude`, `longitude` | Float | Geographic coordinates |
| `province` | String(2) | 2-letter code (AB, BC, ON, etc.) |
| `data_source` | String | `eccc`, `alberta`, or `both` |
| `basin_number` | String | Alberta basin code (BOW, RED, OLD, etc.; nullable for non-AB) |
| `catchment_number` | String | Alberta sub-basin (05AA, 05AB, etc.; nullable for non-AB) |
| `drainage_basin_prefix` | String | First 2 digits of station_number (national grouping) |
| `status` | String | Active / Discontinued (from ECCC; nullable) |
| `real_time` | Boolean | From ECCC; assumed true for Alberta |
| `drainage_area_gross` | Float | km² (from ECCC; nullable) |
| `drainage_area_effect` | Float | km² (from ECCC; nullable) |
| `contributor` | String | Operating agency (from ECCC; nullable) |
| `vertical_datum` | String | Reference datum (from ECCC; nullable) |
| `rhbn` | Boolean | Reference Hydrometric Basin Network (from ECCC; nullable) |
| `has_capacity` | Boolean | Reservoir tracking (from Alberta; nullable) |
| `data_type` | String | HG (water) or PC (precipitation) (from Alberta; nullable) |
| `extra` | JSON | Provider-specific metadata (TSIDs, dataset URLs, etc.) |

### `current_readings`

Latest readings with ratings and source tracking.

| Column | Type | Description |
|---|---|---|
| `station_number` | String (FK) | References `stations` |
| `datetime_utc` | DateTime | Reading timestamp in UTC |
| `fetched_at` | DateTime | When our backend fetched it |
| `data_source` | String | Which provider supplied this reading |
| `water_level` | Float | Metres |
| `discharge` | Float | m³/s |
| `level_symbol` | String | Data quality flag (from ECCC; nullable) |
| `discharge_symbol` | String | Data quality flag (from ECCC; nullable) |
| `outflow` | Float | Reservoir outflow (nullable) |
| `capacity` | Float | Reservoir capacity in dam³ (nullable) |
| `pct_full` | Float | Reservoir percent full (nullable) |
| `flow_rating`, `level_rating`, `pct_full_rating` | String | Computed rating labels |
| `flow_percentiles`, `level_percentiles` | JSON | P10/P25/P50/P75/P90 thresholds |
| `extra` | JSON | Provider-specific data (precipitation totals, etc.) |

### `station_weather`

Cached weather data per station, fetched on demand from Open-Meteo. Each row is keyed by `station_number` (unique) and refreshed when a user requests weather and the cached data is older than 30 minutes.

| Column | Type | Description |
|---|---|---|
| `station_number` | String (FK, unique) | References `stations` |
| `weather_data` | JSON | Full weather blob: `{current, daily_forecast, air_quality, elevation_m}` |
| `weather_fetched_at` | DateTime | Naive UTC timestamp of last fetch |

Created by Alembic migration `c4e7f2d93a10`.

### `historical_daily_means`

Daily mean flow/level keyed by MM-DD and year for percentile calculations.

| Column | Type | Description |
|---|---|---|
| `station_number` | String (FK) | References `stations` |
| `data_key` | String | `flow` or `level` |
| `month_day` | String | MM-DD format |
| `year` | Integer | Calendar year |
| `value` | Float | Daily mean value |
| `data_source` | String | Which provider supplied this data |

### `users` and `favorite_stations`

Standard user accounts with hashed passwords and a join table linking users to their saved stations. Favourites reference `station_number`.

---

## Weather and Air Quality Detail

Weather data is fetched on demand from Open-Meteo when a user requests `GET /api/stations/{station_number}/weather`. The backend caches results in the `station_weather` table for 30 minutes. If the cache is fresh, the response is instant (no external API call). The variables were chosen specifically for people visiting rivers and reservoirs — anglers checking wind before a fishing trip, kayakers assessing conditions, or families planning a day at a reservoir.

### How the Cache Works

1. Frontend calls `GET /api/stations/{station_number}/weather`
2. `weather_cache.py` checks the `station_weather` table for this station
3. If a row exists and `weather_fetched_at` is less than 30 minutes ago, return cached `weather_data`
4. Otherwise, `weather.py` fetches from Open-Meteo (forecast + AQI) for that single station's coordinates
5. The result is upserted into `station_weather` and returned to the caller

This means weather is never fetched for stations nobody is looking at, and popular stations get near-instant responses most of the time.

### Retry Logic

`weather.py` includes exponential backoff for Open-Meteo 429 (rate limit) responses. Up to `WEATHER_MAX_RETRIES` (3) attempts are made with increasing delays. This prevents transient rate limits from causing failures during periods of high traffic.

### Current Conditions

| Variable | Unit | Why It Matters for River Users |
|---|---|---|
| `temperature_2m` | °C | Personal comfort and safety planning |
| `apparent_temperature` | °C | Feels-like temperature accounting for wind chill — critical near open water |
| `precipitation` | mm | Current precipitation intensity |
| `weather_code` | WMO code | Identifies precipitation type (rain, snow, thunderstorm — see interpretation below) |
| `visibility` | metres | Navigation and safety on water, especially for boaters |
| `wind_speed_10m` | km/h | Paddling and boating conditions |
| `wind_gusts_10m` | km/h | Gusts are more dangerous than steady wind for small watercraft |
| `wind_direction_10m` | degrees | Headwind vs tailwind planning for paddlers |
| `uv_index` | 0-11+ | Sun exposure on open water with no shade is significantly higher |
| `is_day` | boolean | Day/night status for icon display |
| `sunrise` / `sunset` | ISO time | Daylight planning — pulled from daily data for today |

### 7-Day Daily Forecast

Each day includes: max/min temperature, max/min apparent temperature, precipitation sum (mm), precipitation probability (%), max wind speed, max wind gusts, sunrise/sunset, max UV index, mean visibility, and weather code.

### Air Quality

| Variable | Unit | Description |
|---|---|---|
| `us_aqi` | 0-500 | US Air Quality Index (overall score) |
| `pm2_5` | µg/m³ | Fine particulate matter — wildfire smoke, vehicle emissions |
| `pm10` | µg/m³ | Coarse particulate matter — dust, pollen |

Air quality is especially important for Alberta and British Columbia, where wildfire smoke seasons can push AQI above 200, making outdoor activities near water unsafe even on otherwise pleasant days.

### Frontend Interpretation Guide

The backend sends raw numerical values. The frontend is responsible for translating these into user-friendly categories.

**WMO Weather Codes** (from the `weather_code` field):

| Code Range | Meaning |
|---|---|
| 0 | Clear sky |
| 1-3 | Mainly clear, partly cloudy, overcast |
| 45-48 | Fog and depositing rime fog |
| 51-55 | Drizzle (light, moderate, dense) |
| 56-57 | Freezing drizzle |
| 61-65 | Rain (slight, moderate, heavy) |
| 66-67 | Freezing rain |
| 71-75 | Snow fall (slight, moderate, heavy) |
| 77 | Snow grains |
| 80-82 | Rain showers (slight, moderate, violent) |
| 85-86 | Snow showers |
| 95 | Thunderstorm (slight or moderate) |
| 96-99 | Thunderstorm with hail |

**Visibility Categories** (from the `visibility` field in metres):

| Range | Category | Implication |
|---|---|---|
| Below 200m | Dense fog | Unsafe for boating |
| 200-1,000m | Foggy | Caution on water |
| 1,000-4,000m | Mildly foggy | Reduced visibility |
| 4,000-10,000m | Clear | Normal conditions |
| Above 10,000m | Very clear | Excellent visibility |

**Air Quality Categories** (from the `us_aqi` field):

| AQI Range | Category | Outdoor Activity Advice |
|---|---|---|
| 0-50 | Good | No restrictions |
| 51-100 | Moderate | Unusually sensitive people should limit prolonged outdoor exertion |
| 101-150 | Unhealthy for sensitive groups | Sensitive groups should reduce outdoor exertion |
| 151-200 | Unhealthy | Everyone should reduce prolonged outdoor exertion |
| 201-300 | Very unhealthy | Everyone should avoid prolonged outdoor exertion |
| 301+ | Hazardous | Everyone should avoid all outdoor exertion |

**Sunrise/Sunset** are available in both the current weather object (today's values) and in each day of the 7-day forecast, so the frontend can easily show "Sunset in 2h 15m" or display daylight hours for trip planning.

---

## Rating Methodology

### Flow and Level Ratings (Rivers and Reservoirs)

Flow and water level ratings are based on historical percentiles, calculated from accumulated daily mean values across multiple years.

**Step 1 — Historical Data Accumulation:** The historical sync downloads daily mean flow/level for each station. Each calendar date is keyed as MM-DD (e.g., `03-19`). Up to 5 years of data are retained per station per date, with older data pruned automatically.

**Step 2 — Percentile Computation:** During each readings refresh, percentiles are computed on the fly. For a given target date, the service collects all stored daily mean values within a ±7 day window across all available years, sorts them, and computes P10, P25, P50, P75, and P90 using linear interpolation. A minimum of 5 historical values is required.

**Step 3 — Rating Assignment:**

| Rating | Condition | Interpretation |
|---|---|---|
| Very Low | Current value < P10 | Unusually low for this time of year |
| Low | P10 ≤ value < P25 | Below the normal range |
| Average | P25 ≤ value ≤ P75 | Within the normal range |
| High | P75 < value ≤ P90 | Above the normal range |
| Very High | value > P90 | Unusually high for this time of year |

Ratings are seasonally adjusted. A flow of 50 m³/s might be "Average" in March but "Low" in June when spring melt typically produces higher flows.

### Reservoir Fullness Rating

Reservoirs with capacity data use a fixed scale rather than historical percentiles:

| Rating | % Full |
|---|---|
| Very Low | Below 20% |
| Low | 20% to 39% |
| Average | 40% to 70% |
| High | 71% to 90% |
| Very High | Above 90% |

---

## Architecture Decisions

This section explains *why* certain design choices were made. Understanding the reasoning helps when extending the system or deciding whether a pattern still applies to your use case.

### Why Cookie-Based Auth Instead of Token Headers?

Most tutorials show JWTs sent in an `Authorization: Bearer <token>` header, stored in `localStorage`. WaterPulse uses HTTPOnly cookies instead.

**The problem with localStorage:** Any JavaScript on the page can read `localStorage`. If an attacker injects a script (XSS), they can steal the token, send it to their server, and impersonate the user indefinitely. The token works from any device — no need to stay on your site.

**How cookies help:** HTTPOnly cookies are invisible to JavaScript. Even if XSS happens, the attacker's script can't read the cookie. The browser sends it automatically, but only to the same origin. A stolen XSS payload can make requests *while the user is on the page*, but can't exfiltrate the token for use elsewhere.

**The tradeoff:** Cookies require CSRF protection (the `X-CSRF-Token` double-submit pattern). This adds complexity but is a well-understood, battle-tested approach.

### Why the Provider/Adapter Pattern?

The simplest approach would be to call the Alberta API and ECCC API directly from the orchestrator functions. The provider pattern adds a layer of abstraction. Why bother?

1. **The APIs are radically different.** Alberta returns triple-encoded JSON with nested data. ECCC returns standard GeoJSON. Mixing parsing logic with merge/rating logic would make both harder to understand and test.

2. **Adding provinces shouldn't require touching existing code.** When a BC or Saskatchewan API becomes available, you create one file and add one line to the registry. The orchestrators, routes, models, and schemas don't change. This is the [Open-Closed Principle](https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle) in practice.

3. **Each provider can be tested in isolation.** `test_providers.py` hits each API independently. If Alberta's format changes, you know exactly which file to fix without tracing through orchestrator logic.

### Why Store Datetimes in UTC?

Reading timestamps from ECCC arrive in UTC. Alberta readings arrive in MST/MDT. Rather than converting everything to a local timezone on the backend, the backend stores everything as naive UTC.

**Why:** The frontend knows the user's local timezone (from the browser). A user in Ontario viewing a BC station expects to see times in their own timezone, not BC time. If the backend picks a timezone, it picks wrong for most users. By storing UTC and letting the frontend convert, every user gets the right time.

### Why Alberta Runs First (Priority Order)?

The 374 stations that exist in both APIs report nearly identical water levels and flows. But Alberta's data includes fields ECCC doesn't have: precipitation totals (6h/12h/24h/48h), reservoir capacity and percent full, station type classification, and basin/catchment grouping.

Running Alberta first and using first-write-wins for readings means shared stations automatically get the richer Alberta data. ECCC's contribution for these stations is limited to metadata fields (drainage area, contributor, status) that Alberta doesn't provide.

### Why Equirectangular Distance Instead of PostGIS?

The `/nearby` endpoint uses a simple math formula instead of PostgreSQL's PostGIS extension for geographic queries.

**Why:** PostGIS is a powerful spatial database extension, but it adds a significant dependency (requires system-level installation, separate from `pip`). The equirectangular approximation is accurate to within 0.5% for distances under 500 km at Canadian latitudes, which is more than sufficient for "find stations near me." The bounding-box pre-filter in SQL reduces candidates before the Python distance calculation runs, keeping it fast even with 8,500+ stations.

If the project later needs complex spatial queries (polygon intersections, river network distance), PostGIS would be worth the dependency.

### Why Upsert Instead of Delete-All for `current_readings`?

The readings refresh uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` (upsert) keyed on `station_number`. This means:

1. **Selective refresh works.** Passing `province=AB` only updates Alberta readings — existing readings for BC, ON, etc. are preserved. Delete-all would wipe unrelated provinces.

2. **`fetched_at` tracks freshness.** Each upsert sets `fetched_at` to the current UTC time. The frontend can check how recent a reading is and show appropriate staleness indicators.

3. **No data loss on partial failure.** If one provider fails, stations covered by other providers still have their existing readings. A delete-all approach would leave the table empty if the re-insert failed.

### Why the `extra` JSON Column?

Each provider has unique fields that don't warrant dedicated columns:

- **Alberta:** precipitation totals, TSIDs (fetch identifiers), dataset URLs (CSV download links), reservoir capacity TSIDs, WMO reporting flag
- **ECCC:** currently empty (all useful fields are in dedicated columns)

Rather than adding columns for every provider-specific field (which would be mostly NULL for other providers), the `extra` JSON column serves as an escape hatch. The orchestrator passes it through without interpreting it. Provider-specific frontend features (like showing precipitation totals for Alberta stations) read from `extra`.

---

## Gotchas and Lessons Learned

Hard-won knowledge from building this system. Check here first when something unexpected happens.

### Alberta's Triple-Encoded JSON

The Alberta API response for stations looks like normal JSON, but the `stations` field contains a *JSON string* rather than a JSON object. Parsing the outer JSON gives you a string that must be parsed a second time. That inner JSON then contains a `WISKI_ABRivers_station_parameters` key whose value is a JSON string that must be parsed a *third* time.

```python
# What you'd expect:
data = response.json()
stations = data["stations"]  # A list of station dicts — nope!

# What actually happens:
data = response.json()                           # Outer JSON
stations_str = data["stations"]                   # A string containing JSON
stations_obj = json.loads(stations_str)           # Parse the string
station_list = stations_obj["WISKI_ABRivers_station_parameters"]  # The actual list
```

The Alberta provider handles all of this. If you see `json.loads()` being called on what looks like already-parsed data, this is why.

### ECCC Coordinates Are [Longitude, Latitude]

GeoJSON standard puts longitude first: `[lon, lat]`. This is the opposite of what most people expect (Google Maps, GPS, everyday usage all put latitude first). The ECCC provider swaps these during normalization.

If you see coordinates around `[-114, 51]` that's Calgary. If you see `[51, -114]`, the swap was missed.

### Alberta Timestamps Are Mountain Time

The Alberta API returns reading timestamps in MST/MDT (Mountain Time), not UTC. The Alberta provider converts these to naive UTC using `ZoneInfo("America/Edmonton")` before returning them as `NormalizedReading.datetime_utc`. If you see readings that are 6-7 hours off from expected, this conversion may have been skipped.

Similarly, `fetched_at` (when the backend fetched the data) uses `datetime.now(timezone.utc).replace(tzinfo=None)` to ensure it's stored as naive UTC regardless of the server's local timezone.

### Auto-Created Stations

ECCC's real-time feed sometimes reports readings for stations not in the metadata collection. Rather than discarding these readings (losing data), the readings refresh auto-creates minimal station records with `station_name` set to the station number as a placeholder.

These stub records get enriched on the next station sync when the provider fetches full metadata. If you see stations with names like `"07GE008"` (just the number), they were auto-created and haven't been synced yet.

### Weather Is Now On-Demand (Not in Bulk Refresh)

Weather used to be fetched for every station during the 10-minute readings refresh, which added 15-30 seconds to each cycle. Now weather is fetched on demand per station via `GET /api/stations/{station_number}/weather` and cached for 30 minutes in the `station_weather` table. This made the readings refresh significantly faster (3 phases instead of 4) and eliminated unnecessary Open-Meteo calls for stations nobody is viewing.

Weather data is served exclusively from the `station_weather` table via the dedicated weather endpoint.

### Historical Sync Is a Long Job

The initial historical sync for all of Canada downloads 5 years of daily means for thousands of stations. For ECCC stations, this means paginated API calls at 10,000 rows per request. For Alberta stations, this means downloading and parsing 365-day CSV files.

Expect the first full run to take up to 1.5 hours. Subsequent runs are similar in duration because every station is re-synced, but the upsert only writes changed values. Inserts are batched (200 rows per statement) to avoid connection drops in containerised environments.

### Minimum 5 Values for Percentiles

If a station has fewer than 5 historical daily mean values in the ±7 day window, no rating is computed. The reading is stored without a rating, and the frontend should handle the `null` rating gracefully (show "insufficient data" rather than leaving a blank space).

New stations or recently added provinces will have no ratings until historical data is synced.

---

## Testing Strategies

### Test Files

WaterPulse uses standalone test scripts that run against live APIs and the real database:

| File | What It Tests |
|---|---|
| `test_providers.py` | Each provider's fetch methods against live APIs (no database) |
| `test_merge_write.py` | Reading freshness, merge logic, and database writes |
| `test_orchestrators.py` | Full station sync and readings refresh through the database |

### Running Tests

```bash
cd waterpulse-backend
python test_providers.py        # Tests providers, outputs test_results.json
python test_merge_write.py      # Tests merge logic, outputs test_merge_results.json
python test_orchestrators.py    # Tests full pipeline, outputs test_orchestrator_results.json
```

### What to Test After Changes

| You Changed... | Run This |
|---|---|
| A provider file | `test_providers.py` |
| Merge logic or station sync | `test_orchestrators.py` |
| Reading parsing or deduplication | `test_merge_write.py` |
| Database models | Run Alembic migration first, then all tests |
| Schemas or routes | Start the server and test via `http://localhost:8000/docs` |

### Testing with FastAPI's Docs

FastAPI's auto-generated Swagger UI at `/docs` lets you test any endpoint interactively:

1. Start the server: `uvicorn app.main:app --reload`
2. Open `http://localhost:8000/docs`
3. Click any endpoint, click "Try it out", fill in parameters, click "Execute"
4. See the actual response, status code, and headers

### Integration vs Unit Testing

The current tests are **integration tests** — they hit live APIs and the real database. This is intentional because:

- The external APIs are the most likely thing to break (format changes, downtime)
- Database writes reveal issues that mocking would hide (FK constraints, type mismatches)
- The data is publicly available (no secrets or side effects in read-only tests)

For future development, consider adding **unit tests** with `pytest` for:
- Percentile computation (pure math, no I/O)
- Station merge logic (pure data transformation)
- CSV parsing (can use fixture files)

---

## Common Tasks

### Adding a New Column to a Table

1. Add the field to the model:
   ```python
   # In models/station.py:
   new_field: Mapped[str | None] = mapped_column(String(50))
   ```

2. Add it to the schema if the API should return it:
   ```python
   # In schemas/__init__.py:
   new_field: str | None = None
   ```

3. Generate and apply the migration:
   ```bash
   alembic revision --autogenerate -m "Add new_field to stations"
   alembic upgrade head
   ```

### Adding a New API Endpoint

1. Add the route function:
   ```python
   # In routes/stations.py:
   @router.get("/my-endpoint")
   async def my_endpoint(
       param: str = Query(...),
       db: AsyncSession = Depends(get_db),
   ):
       # Your logic here
       return results
   ```

2. Add a Pydantic schema if the response needs a new shape.

3. The endpoint automatically appears in `/docs`.

### Adding a New Data Provider

1. Create `app/services/providers/bc_provider.py`:
   ```python
   class BCProvider(BaseProvider):
       @property
       def name(self) -> str:
           return "bc"

       async def fetch_stations(self) -> list[NormalizedStation]:
           # Your fetch + parse logic

       async def fetch_latest_readings(self) -> list[NormalizedReading]:
           # Your fetch + parse logic

       async def fetch_historical_daily_means(self, station_number, start_date, end_date):
           # Your fetch + parse logic
   ```

2. Register it in `providers/__init__.py`:
   ```python
   from app.services.providers.bc_provider import BCProvider

   _PROVIDERS = [AlbertaProvider(), BCProvider(), ECCCProvider()]
   ```

3. Add any new config values to `config.py` and `.env`.

4. No changes needed to orchestrators, routes, models, or schemas.

### Debugging a Failed Reading Refresh

1. Check the scheduler log: look for `"Scheduled refresh failed"` errors
2. Run manually: `curl -X POST http://localhost:8000/api/admin/refresh-readings`
3. Check the status: `curl http://localhost:8000/api/admin/status`
4. Run the test script: `python test_orchestrators.py`
5. Check the JSON output for error details and tracebacks

### Checking Data Freshness

```bash
curl http://localhost:8000/api/readings/last-updated
# Returns: {"last_updated": "2026-04-01T03:38:...", "server_time": "..."}

curl http://localhost:8000/api/admin/status
# Returns full breakdown by province, source, type
```

### After Schema Changes

```bash
# 1. Edit the model file (e.g. models/station.py)
# 2. Generate a migration
alembic revision --autogenerate -m "Describe what changed"
# 3. Review the generated file in alembic/versions/
# 4. Apply it
alembic upgrade head
```

---

## Docker

### Dockerfile

The backend Dockerfile (`waterpulse-backend/Dockerfile`) uses Python 3.12-slim (Debian-based, not Alpine) because the `asyncpg` and `psycopg2-binary` packages include C extensions that compile more reliably on Debian.

**Layer caching strategy:** `requirements.txt` is copied and installed before the source code. This means changing a Python file does NOT re-trigger `pip install` — only changes to `requirements.txt` invalidate the dependency layer, making rebuilds fast.

### entrypoint.sh

The entrypoint script runs every time the backend container starts:

1. **Wait for PostgreSQL** — uses `psycopg2` with individual connection params (`host` from `POSTGRES_HOST` env var defaulting to `db`, `password` from `POSTGRES_PASSWORD` env var) to verify the database accepts queries. Retries every 2 seconds for up to 30 attempts. We use individual params instead of `DATABASE_URL_SYNC` because the SQLAlchemy dialect prefix (`postgresql+psycopg2://`) is not valid for raw psycopg2. The `POSTGRES_HOST` default of `db` matches the docker-compose service name; in Kubernetes, the ConfigMap sets it to `db-service`.
2. **Run Alembic migrations** — `alembic upgrade head` brings the schema to the latest version. If this fails, the container stops (the API will not start with an outdated schema).
3. **Start uvicorn** — serves the FastAPI app on `0.0.0.0:8000`. Extra arguments from docker-compose `command` (e.g., `--reload`) are passed through.

> **Windows users:** This file must use LF line endings, not CRLF. The `.gitattributes` rule `*.sh text eol=lf` handles this automatically.

### Environment Variables in Docker

| Variable | Set Where | Notes |
|----------|-----------|-------|
| `DATABASE_URL` | `docker-compose.yml` | Uses Docker service name `db` as hostname — only works inside Docker network |
| `DATABASE_URL_SYNC` | `docker-compose.yml` | Same, but sync driver for Alembic |
| `POSTGRES_PASSWORD` | `.env` | Shared by the `db` and `backend` containers |
| `SECRET_KEY`, API URLs, etc. | `.env` | Loaded via `env_file` directive in docker-compose |

> **Important:** The backend's pydantic-settings configuration reads all required environment variables at import time (when the Python process starts). If any required variable is missing, the container crashes immediately with a pydantic validation error. Check `docker-compose logs backend` if the container exits on startup.

### Alembic in Docker

Migrations run automatically on container start. For manual operations:

```bash
# Apply all pending migrations
docker-compose exec backend alembic upgrade head

# Create a new migration from model changes
docker-compose exec backend alembic revision --autogenerate -m "description of change"

# Check current migration state
docker-compose exec backend alembic current
```

### Connecting to the Database

Port 5432 is exposed in the development docker-compose for local tools (pgAdmin, DBeaver, etc.):

```bash
# Open a psql shell inside the container
docker-compose exec db psql -U waterpulse -d waterpulse

# Or connect from your host machine
psql -h localhost -p 5432 -U waterpulse -d waterpulse
```

### .dockerignore

The `.dockerignore` file excludes `__pycache__/`, `.venv/`, `.env` files, and test artifacts from the Docker build context. This:
- Prevents secrets (`.env`) from being copied into the Docker image
- Keeps the build context small and builds fast (the `.venv/` alone can be 200+ MB)
- Avoids stale bytecode (`__pycache__/`) interfering with the container's Python runtime

---

## Kubernetes

The backend runs identically on a local kind cluster. See `k8s/README.md` in the project root for the full setup guide.

### Key differences from Docker Compose

| Aspect | Docker Compose | Kubernetes |
|--------|---------------|------------|
| Database hostname | `db` (service name) | `db-service` (K8s Service name, set via `POSTGRES_HOST` in ConfigMap) |
| Database URL | Set in `docker-compose.yml` | Constructed in `backend-deployment.yaml` using `$(POSTGRES_PASSWORD)` K8s variable interpolation |
| Secrets | `.env` file | `k8s/secrets.yaml` (base64-encoded, gitignored) |
| Config | `.env` file | `k8s/configmap.yaml` (plain text, committed) |
| Reverse proxy | Nginx container | NGINX Ingress Controller (cluster addon) |
| Historical sync | APScheduler (inside uvicorn process) | CronJob (`job-historical-sync.yaml`) — dedicated pod |
| Image loading | Automatic (build context) | Manual: `docker build` then `kind load docker-image` |

### Backend-specific K8s notes

- **startupProbe** allows 120 seconds for Alembic migrations to complete before Kubernetes considers the pod failed
- **envFrom: configMapRef** injects all ConfigMap keys as environment variables (equivalent to docker-compose `env_file`)
- **secretKeyRef** pulls `POSTGRES_PASSWORD` and `SECRET_KEY` from the K8s Secret
- **DATABASE_URL** uses K8s-native variable interpolation: `$(POSTGRES_PASSWORD)` is replaced with the actual value at pod startup
- **entrypoint.sh** reads `POSTGRES_HOST` from the environment (defaults to `db` for backward compatibility with docker-compose)
- **Historical sync** runs as a CronJob (Jan 1st at 03:00 UTC) in its own pod, avoiding liveness probe kills and Ingress timeouts. Trigger manually with: `kubectl create job --from=cronjob/historical-sync manual-sync -n waterpulse`

### Common K8s commands for the backend

```bash
# View backend logs
kubectl logs deployment/backend -n waterpulse

# Follow logs in real-time
kubectl logs -f deployment/backend -n waterpulse

# Open a shell in the backend pod
kubectl exec -it deployment/backend -n waterpulse -- /bin/bash

# Restart after code changes
docker build -t waterpulse-backend:latest ./waterpulse-backend
kind load docker-image waterpulse-backend:latest --name waterpulse
kubectl rollout restart deployment/backend -n waterpulse

# Run Alembic manually inside the pod
kubectl exec deployment/backend -n waterpulse -- alembic upgrade head
kubectl exec deployment/backend -n waterpulse -- alembic current

```

---

## Data Disclaimer

All water data provided through this application is provisional and preliminary in nature. Data is sourced from Environment and Climate Change Canada (ECCC) and provincial networks including Rivers Alberta.

> Data is automatically generated by remote equipment that may not be under the control of the respective government agencies. This data has not been reviewed or edited for accuracy and may be subject to significant change when reviewed or corrected. Please exercise caution and carefully consider the provisional nature of the information provided. The data providers assume no responsibility for the accuracy or completeness of this data and any use of it is therefore entirely at your own risk.
