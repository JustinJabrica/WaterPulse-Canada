"""
Background scheduler — currently unused.

Readings refresh is now triggered on demand by the frontend via
POST /api/readings/refresh. This file is kept as a placeholder
in case periodic background tasks are needed in the future
(e.g. data cleanup, health checks).
"""

import logging

logger = logging.getLogger(__name__)


def start_scheduler():
    """No-op — scheduler disabled in favour of frontend-driven refresh."""
    logger.info("Scheduler disabled: readings refresh is now on-demand")


def stop_scheduler():
    """No-op — nothing to stop."""
    pass
