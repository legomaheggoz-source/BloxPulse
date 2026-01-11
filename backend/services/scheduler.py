"""
Scheduler Service

Handles scheduled data collection tasks using APScheduler.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from database import async_session_maker
from collectors.roblox import run_collection


logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def collect_data_job():
    """Scheduled job to collect data from all sources."""
    logger.info(f"Starting scheduled data collection at {datetime.utcnow()}")

    async with async_session_maker() as session:
        try:
            results = await run_collection(session)
            await session.commit()
            logger.info(f"Data collection completed: {results}")
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            await session.rollback()


def setup_scheduler() -> AsyncIOScheduler:
    """
    Set up the APScheduler for background tasks.

    Returns the scheduler instance.
    """
    global scheduler

    scheduler = AsyncIOScheduler()

    # Add data collection job
    scheduler.add_job(
        collect_data_job,
        trigger=IntervalTrigger(hours=settings.collection_interval_hours),
        id="data_collection",
        name="Collect trending games data",
        replace_existing=True,
    )

    logger.info(
        f"Scheduler configured: data collection every {settings.collection_interval_hours} hours"
    )

    return scheduler


def get_scheduler() -> AsyncIOScheduler:
    """Get the scheduler instance."""
    return scheduler


async def trigger_collection():
    """Manually trigger a data collection run."""
    await collect_data_job()
