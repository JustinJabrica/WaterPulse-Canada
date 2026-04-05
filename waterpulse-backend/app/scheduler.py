"""
Background scheduler — runs periodic tasks without user interaction.

Jobs:
  1. Readings refresh — every READINGS_REFRESH_INTERVAL_MINUTES (default 10).
     Keeps station data fresh so users always see recent readings without
     needing to trigger a manual refresh.

  2. Historical sync — once per year on January 1st at 03:00 UTC.
     Re-fetches 5 years of daily mean data for percentile calculations.
     Runs at 03:00 to avoid overlap with normal traffic.

Both jobs use APScheduler's AsyncIOScheduler, which shares the uvicorn
event loop. Each job creates its own database session (not tied to any
HTTP request) and commits/closes it when done.

max_instances=1 prevents overlap if a job takes longer than its interval.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_readings_refresh():
    """
    Scheduled job: refresh current readings for all provinces.

    Creates its own DB session since scheduled jobs run outside of
    any HTTP request context. Catches all exceptions so a single
    failed run doesn't kill the scheduler.
    """
    from app.services.readings_refresh import refresh_current_readings

    logger.info("Scheduler: starting readings refresh...")
    try:
        async with async_session() as db:
            result = await refresh_current_readings(db)
            logger.info(f"Scheduler: readings refresh complete — {result}")
    except Exception as e:
        logger.error(f"Scheduler: readings refresh failed — {e}", exc_info=True)


async def _run_historical_sync():
    """
    Scheduled job: sync historical daily means for all provinces.

    Runs once per year to rebuild the percentile table with the latest
    5 years of data. This is a long-running job (can take hours for
    all of Canada), so max_instances=1 is critical.
    """
    from app.services.historical_sync import sync_historical_data

    logger.info("Scheduler: starting annual historical sync...")
    try:
        result = await sync_historical_data()
        logger.info(f"Scheduler: historical sync complete — {result}")
    except Exception as e:
        logger.error(f"Scheduler: historical sync failed — {e}", exc_info=True)


def start_scheduler():
    """Register jobs and start the scheduler."""

    # ── Readings refresh: every N minutes ────────────────────────
    scheduler.add_job(
        _run_readings_refresh,
        trigger=IntervalTrigger(minutes=settings.READINGS_REFRESH_INTERVAL_MINUTES),
        id="readings_refresh",
        name="Refresh current readings",
        max_instances=1,
        replace_existing=True,
    )

    # ── Historical sync: January 1st at 03:00 UTC ───────────────
    scheduler.add_job(
        _run_historical_sync,
        trigger=CronTrigger(month=1, day=1, hour=3, minute=0),
        id="historical_sync",
        name="Annual historical data sync",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: readings refresh every "
        f"{settings.READINGS_REFRESH_INTERVAL_MINUTES} min, "
        f"historical sync on Jan 1st at 03:00 UTC"
    )


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
