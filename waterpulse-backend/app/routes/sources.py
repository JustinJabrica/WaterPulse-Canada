"""
Source-status endpoint for the /methodology live source-status table.

GET /api/sources/status → per-source health map (see app.services.source_health).
Read-only, cheap: composes a committed DS-STD probe snapshot with live ingestion
freshness from the DB — it never re-probes external sources on request.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.source_health import build_status

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("/status")
async def sources_status(db: AsyncSession = Depends(get_db)):
    """Per-source health for the methodology page's status indicators."""
    return await build_status(db)
