"""
FastAPI application entry point for InvestIQ.

Startup:
  1. Create data/ directory if not exists
  2. Initialize SQLite schema
  3. Start APScheduler with morning briefing job at 07:00 IST
  4. Generate briefing immediately if no cached briefing exists
  5. Apply CORS middleware for localhost:3000

Shutdown:
  - Stop APScheduler cleanly
"""
import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.database import create_schema
from backend.api.health import router as health_router
from backend.api.portfolio import router as portfolio_router
from backend.api.indices import router as indices_router
from backend.api.fx import router as fx_router
from backend.api.briefing import router as briefing_router
from backend.api.refresh import router as refresh_router
from backend.api.chat import router as chat_router
from backend.api.alerts import router as alerts_router
from backend.scheduler import init_scheduler
from backend.core.briefing import BriefingOrchestrator
from backend.core.portfolio import resolve_tr_yfinance_tickers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup → yield → shutdown."""
    # Startup
    data_dir = os.path.dirname(settings.DB_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    create_schema(settings.DB_PATH)

    # Resolve any TR ISINs → yfinance tickers that weren't mapped yet (best-effort)
    try:
        resolved = resolve_tr_yfinance_tickers(settings.DB_PATH)
        if resolved:
            logger.info("Resolved %d TR ISIN → yfinance tickers on startup", resolved)
    except Exception as exc:
        logger.warning("TR ticker resolution on startup failed (non-fatal): %s", exc)

    # Start APScheduler with morning briefing at 08:55 Europe/Berlin
    scheduler = BackgroundScheduler()
    init_scheduler(scheduler, settings.DB_PATH)
    scheduler.start()
    logger.info("APScheduler started — morning briefing at 08:55 Europe/Berlin")

    # On startup: if no briefing exists for today, schedule first run at 09:00 Berlin.
    # If a briefing already exists for today, do nothing (user restarted mid-day).
    try:
        from datetime import datetime
        import pytz
        berlin = pytz.timezone("Europe/Berlin")
        today_berlin = datetime.now(berlin).strftime("%Y-%m-%d")
        orchestrator = BriefingOrchestrator(settings.DB_PATH)
        latest = orchestrator.get_latest()
        latest_date = (latest or {}).get("briefing_date")
        if latest_date != today_berlin:
            # No briefing for today yet — add a one-shot job at 09:00 Berlin
            from apscheduler.triggers.cron import CronTrigger
            scheduler.add_job(
                lambda: orchestrator.generate(),
                CronTrigger(hour=9, minute=0, second=0, timezone="Europe/Berlin"),
                id="first_run_today",
                replace_existing=True,
            )
            logger.info("No briefing for today — scheduled first run at 09:00 Europe/Berlin")
        else:
            logger.info("Briefing for today already exists — skipping startup generation")
    except Exception as exc:
        logger.warning("Startup briefing scheduling failed (non-fatal): %s", exc)

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="InvestIQ", version="0.1.0", lifespan=lifespan)

# CORS: allow only local frontend origins (T-01-05 mitigation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(indices_router)
app.include_router(fx_router)
app.include_router(briefing_router)
app.include_router(refresh_router)
app.include_router(chat_router)
app.include_router(alerts_router)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
