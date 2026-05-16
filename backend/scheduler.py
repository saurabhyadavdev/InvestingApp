"""
APScheduler setup for InvestIQ.

Registers the morning briefing job at 07:00 IST daily.
The scheduler is started and stopped by FastAPI's lifespan handler in main.py.

Security note (T-04-04):
  BriefingOrchestrator.generate() is wrapped in try/except at the job level
  to prevent APScheduler process crashes on data-fetch failures.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _run_morning_briefing(db_path: str) -> None:
    """
    Wrapper that calls BriefingOrchestrator.generate() inside a try/except.
    This prevents APScheduler from marking the job as failed and crashing
    the scheduler process (T-04-04 mitigation).
    """
    try:
        # Import here to avoid circular imports at module load time
        from backend.core.briefing import BriefingOrchestrator
        orchestrator = BriefingOrchestrator(db_path)
        result = orchestrator.generate()
        logger.info(
            "Morning briefing generated at %s for date %s",
            result.get("generated_at"),
            result.get("briefing_date"),
        )
    except Exception as exc:
        logger.error("Morning briefing job failed: %s", exc)


def init_scheduler(scheduler: BackgroundScheduler, db_path: str) -> None:
    """
    Register the morning briefing cron job on the given scheduler.

    Parameters
    ----------
    scheduler : BackgroundScheduler
        An APScheduler BackgroundScheduler instance (not yet started).
    db_path : str
        Path to the SQLite database — passed through to BriefingOrchestrator.

    Note: this function does NOT start the scheduler. The caller (main.py lifespan)
    is responsible for calling scheduler.start() and scheduler.shutdown().
    """
    scheduler.add_job(
        _run_morning_briefing,
        CronTrigger(hour=8, minute=55, second=0, timezone="Europe/Berlin"),
        id="morning_briefing",
        replace_existing=True,
        kwargs={"db_path": db_path},
    )
    logger.info("Registered 'morning_briefing' job — fires at 08:55 Europe/Berlin daily")
