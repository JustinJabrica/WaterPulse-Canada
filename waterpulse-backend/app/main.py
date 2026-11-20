import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import get_db, engine, Base
from app.limiter import limiter
from app.models import Station, CurrentReading, HistoricalDailyMean, User
from app.routes import stations, auth, collections, users, tags
from app.routes.admin import router as admin_router
from app.routes.readings import router as readings_router
from app.routes.sources import router as sources_router
from app.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit cookie CSRF protection.

    On state-changing requests (POST/PUT/PATCH/DELETE), compares the
    X-CSRF-Token header against the csrf_token cookie. Only enforced
    when an access_token cookie is present (i.e. for authenticated users).
    Login and register are exempt since they create the cookies.

    /api/admin/* is deliberately NOT exempt: those endpoints now require an
    admin, and a superuser's browser session must prove same-origin like any
    other mutating call. Script callers authenticate with the ADMIN_API_TOKEN
    bearer header and send no cookie, so this check doesn't apply to them.
    """

    EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register", "/api/readings/refresh"}
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in self.PROTECTED_METHODS
            and request.url.path not in self.EXEMPT_PATHS
            and request.cookies.get("access_token")
        ):
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("x-csrf-token")

            if (
                not csrf_cookie
                or not csrf_header
                or not secrets.compare_digest(
                    csrf_cookie.encode("utf-8"), csrf_header.encode("utf-8")
                )
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on boot, stop on shutdown.

    The schema is owned by Alembic — `entrypoint.sh` runs `alembic upgrade
    head` before this lifespan ever fires, and bare-metal local dev expects
    the same. We deliberately do NOT call `Base.metadata.create_all` here:
    it would create tables ahead of an upcoming migration and then make the
    migration's own CREATE TABLE fail with `relation already exists`.
    """
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="WaterPulse API",
    description="Real-time river, lake, and reservoir monitoring data for Canada",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting — per-IP, in-memory (swap to Redis for multi-replica AWS)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow the Next.js frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF protection — validates X-CSRF-Token header on state-changing requests
app.add_middleware(CSRFMiddleware)

# Register routers
app.include_router(stations.router)
app.include_router(readings_router)
app.include_router(auth.router)
app.include_router(collections.router)
app.include_router(users.router)
app.include_router(tags.router)
app.include_router(admin_router)
app.include_router(sources_router)


@app.get("/")
async def root(db: AsyncSession = Depends(get_db)):
    """API root with last updated timestamp."""
    latest_fetch = await db.execute(
        select(func.max(CurrentReading.fetched_at))
    )
    last_updated = latest_fetch.scalar()

    return {
        "name": "WaterPulse API",
        "version": "1.0.0",
        "last_updated": last_updated.isoformat() if last_updated else None,
        "server_time": datetime.now().isoformat(),
        "docs": "/docs",
    }
