"""
Source health for the /methodology live source-status table.

Deliberately low-impact (DS-STD politeness): this does **not** re-probe external
endpoints on a schedule. It composes two cheap signals:

  1. A committed **probe snapshot** (`app/data/source_status_snapshot.json`) —
     the read-only DS-STD coverage result (reachability per source), regenerated
     only when the probe suite is run, never live.
  2. **Live ingestion freshness** for the handful of IMPLEMENTED sources, read
     from the app's own database (the readings/weather the scheduler already
     fetches every ~10 min) — zero additional external calls.

Returns a per-source `{health, data_age_minutes, basis, ...}` map the frontend
renders as pulsing status dots.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading import CurrentReading
from app.models.weather import StationWeather

_SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "data", "source_status_snapshot.json")

# IMPLEMENTED sources whose health is derived live from the DB, with the
# expected ingestion cadence (minutes) used to classify up/degraded/down.
_READINGS_SOURCES = ("SRC-ECCC-DATAMART", "SRC-ECCC-GEOMET", "SRC-AB-RIVERS")
_WEATHER_SOURCES = ("SRC-OPEN-METEO", "SRC-OPEN-METEO-AQI")
_READINGS_CADENCE_MIN = 10   # app scheduler refresh interval
_WEATHER_CADENCE_MIN = 30    # weather cache TTL


def _load_snapshot() -> dict:
    try:
        with open(_SNAPSHOT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"snapshot_date": None, "sources": {}}


# Loaded once at import; the file is a committed artifact.
_SNAPSHOT = _load_snapshot()


def _classify(age_min: float | None, cadence_min: float) -> str:
    """up within ~2 cadences, degraded within ~12, else down/unknown."""
    if age_min is None:
        return "unknown"
    if age_min <= 2 * cadence_min:
        return "up"
    if age_min <= 12 * cadence_min:
        return "degraded"
    return "down"


def _age_minutes(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return round((now - ts).total_seconds() / 60.0, 1)


async def build_status(db: AsyncSession) -> dict:
    """Compose the per-source health map (snapshot + live ingestion freshness)."""
    now = datetime.now(timezone.utc)
    sources: dict[str, dict] = {}

    # 1. Start from the committed probe snapshot (reachability per source).
    for sid, entry in (_SNAPSHOT.get("sources") or {}).items():
        sources[sid] = {
            "health": entry.get("health", "unknown"),
            "data_age_minutes": entry.get("data_age_minutes"),
            "reason": entry.get("reason"),
            "basis": "probe-snapshot",
            "checked_at": _SNAPSHOT.get("snapshot_date"),
        }

    # 2. Overlay LIVE ingestion freshness for implemented sources (DB only).
    readings_age = _age_minutes(
        (await db.execute(select(func.max(CurrentReading.fetched_at)))).scalar(), now
    )
    weather_age = _age_minutes(
        (await db.execute(select(func.max(StationWeather.weather_fetched_at)))).scalar(), now
    )
    for sid in _READINGS_SOURCES:
        sources[sid] = {
            "health": _classify(readings_age, _READINGS_CADENCE_MIN),
            "data_age_minutes": readings_age, "reason": None,
            "basis": "live-ingestion", "checked_at": now.isoformat(timespec="seconds"),
        }
    for sid in _WEATHER_SOURCES:
        sources[sid] = {
            "health": _classify(weather_age, _WEATHER_CADENCE_MIN),
            "data_age_minutes": weather_age, "reason": None,
            "basis": "live-ingestion", "checked_at": now.isoformat(timespec="seconds"),
        }

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "snapshot_date": _SNAPSHOT.get("snapshot_date"),
        "sources": sources,
    }
