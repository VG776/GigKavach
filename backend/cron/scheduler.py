"""
cron/scheduler.py — APScheduler Configuration
──────────────────────────────────────────────────
Centralized scheduler setup for all background jobs:
1. DCI Poller (every 5 minutes)
2. Claims Trigger (every 5 minutes)
3. RSS Parser (every 1 hour)
4. DCI Historical Archival (daily)

Uses APScheduler with in-memory JobStore (for simplicity).
For production, use persistent JobStore (PostgreSQL/Supabase).
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.cron.dci_poller import process_zone
from backend.cron.claims_trigger import trigger_claims_pipeline
from backend.cron.rss_parser import parse_feeds
from backend.config.settings import settings

logger = logging.getLogger("gigkavach.scheduler")

# Global scheduler instance
scheduler = AsyncIOScheduler()


def configure_scheduler():
    """
    Configure and start the APScheduler with all background jobs.
    
    Should be called once at application startup in main.py:
    ```python
    from backend.cron.scheduler import configure_scheduler
    
    @app.on_event("startup")
    async def startup():
        configure_scheduler()
    ```
    """
    
    logger.info("[SCHEDULER] Configuring background jobs...")
    
    # ──────────────────────────────────────────────────────────────────────────
    # 1. DCI Poller (every 5 minutes)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[SCHEDULER] Registering: DCI Poller (every 5 minutes)")
    scheduler.add_job(
        func=dci_poller_scheduled,
        trigger=IntervalTrigger(minutes=5),
        id="dci_poller",
        name="DCI Poller",
        replace_existing=True,
        misfire_grace_time=60,  # Skip if missed by >60s
    )
    
    # ──────────────────────────────────────────────────────────────────────────
    # 2. Claims Trigger (every 5 minutes)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[SCHEDULER] Registering: Claims Trigger (every 5 minutes)")
    scheduler.add_job(
        func=claims_trigger_scheduled,
        trigger=IntervalTrigger(minutes=5),
        id="claims_trigger",
        name="Claims Processing Pipeline",
        replace_existing=True,
        misfire_grace_time=60,  # Skip if missed by >60s
    )
    
    # ──────────────────────────────────────────────────────────────────────────
    # 3. RSS Feed Parser (every 1 hour)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[SCHEDULER] Registering: RSS Parser (every 1 hour)")
    scheduler.add_job(
        func=rss_parser_scheduled,
        trigger=IntervalTrigger(hours=1),
        id="rss_parser",
        name="RSS Feed Parser",
        replace_existing=True,
        misfire_grace_time=300,  # Skip if missed by >5min
    )
    
    # ──────────────────────────────────────────────────────────────────────────
    # 4. DCI Historical Archival (daily at 2 AM UTC)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info("[SCHEDULER] Registering: DCI History Archive (daily 2 AM UTC)")
    scheduler.add_job(
        func=dci_archival_scheduled,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="dci_archival",
        name="DCI Historical Archival",
        replace_existing=True,
        misfire_grace_time=3600,  # Skip if missed by >1 hour
    )
    
    # Start scheduler
    if not scheduler.running:
        scheduler.start()
        logger.info("[SCHEDULER] ✅ Scheduler started successfully")
    else:
        logger.warning("[SCHEDULER] Scheduler already running")


def stop_scheduler():
    """Stop the scheduler (useful for graceful shutdown)."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[SCHEDULER] Scheduler stopped")


# ──────────────────────────────────────────────────────────────────────────┐

async def dci_poller_scheduled():
    """Wrapper for DCI Poller job."""
    try:
        logger.info("[SCHEDULER JOB] DCI Poller starting...")
        
        # Process all active zones
        active_zones = ["560001", "560037", "560034", "560038", "560068"]
        
        tasks = [process_zone(zone) for zone in active_zones]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"[SCHEDULER JOB] DCI Poller completed: {len(results)} zones processed")
        
    except Exception as e:
        logger.error(f"[SCHEDULER JOB ERROR] DCI Poller failed: {str(e)}", exc_info=True)


async def claims_trigger_scheduled():
    """Wrapper for Claims Pipeline job."""
    try:
        logger.info("[SCHEDULER JOB] Claims Trigger starting...")
        result = await trigger_claims_pipeline()
        logger.info(
            f"[SCHEDULER JOB] Claims Trigger completed: "
            f"{result.get('approved', 0)} approved, "
            f"{result.get('rejected', 0)} rejected"
        )
        
    except Exception as e:
        logger.error(f"[SCHEDULER JOB ERROR] Claims Trigger failed: {str(e)}", exc_info=True)


async def rss_parser_scheduled():
    """Wrapper for RSS Parser job."""
    try:
        logger.info("[SCHEDULER JOB] RSS Parser starting...")
        result = await parse_feeds()
        logger.info(f"[SCHEDULER JOB] RSS Parser completed: {result.get('articles_parsed', 0)} articles")
        
    except Exception as e:
        logger.error(f"[SCHEDULER JOB ERROR] RSS Parser failed: {str(e)}", exc_info=True)


async def dci_archival_scheduled():
    """Wrapper for DCI Historical Archival job."""
    try:
        logger.info("[SCHEDULER JOB] DCI Archival starting...")
        
        # TODO: Implement DCI historical archival
        # 1. Query all DCI_LOGS from today
        # 2. Pre-aggregate to hourly + daily summaries
        # 3. Archive to dci_history table
        # 4. Clear old dci_logs (>90 days)
        
        logger.info("[SCHEDULER JOB] DCI Archival completed")
        
    except Exception as e:
        logger.error(f"[SCHEDULER JOB ERROR] DCI Archival failed: {str(e)}", exc_info=True)


# ──────────────────────────────────────────────────────────────────────────┐

def get_scheduler_info():
    """Get info about running jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time),
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "total_jobs": len(jobs)
    }
