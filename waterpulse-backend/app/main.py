import logging
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
from app.models import Station, CurrentReading, HistoricalDailyMean, User, FavoriteStation
from app.routes import stations, auth, favorites
from app.routes.admin import router as admin_router
from app.routes.readings import router as readings_router
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
    """

    EXEMPT_PATHS = {"/api/auth/login", "/api/auth/register", "/api/readings/refresh"}
    EXEMPT_PREFIXES = ("/api/admin/",)
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in self.PROTECTED_METHODS
            and request.url.path not in self.EXEMPT_PATHS
            and not any(request.url.path.startswith(p) for p in self.EXEMPT_PREFIXES)
            and request.cookies.get("access_token")
        ):
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("x-csrf-token")

            if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup, start scheduler, cleanup on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
app.include_router(favorites.router)
app.include_router(admin_router)


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
