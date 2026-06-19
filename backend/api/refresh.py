"""
POST /api/refresh — triggers on-demand briefing regeneration.
"""
import asyncio
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.briefing import BriefingOrchestrator

router = APIRouter(prefix="/api")


@router.post("/refresh")
async def refresh_briefing() -> dict:
    """
    Trigger immediate briefing regeneration outside the scheduled window.

    BriefingOrchestrator.generate() is synchronous (yfinance I/O + SQLite writes).
    Run it in a thread pool to avoid blocking the async event loop.

    Returns
    -------
    dict
        {"status": "Briefing refreshed", "generated_at": str}

    Note: No rate limiting in Phase 1 (T-04-01 accepted — single user local app).
    """
    orchestrator = BriefingOrchestrator(settings.DB_PATH)
    result = await asyncio.to_thread(orchestrator.generate)

    return {
        "status": "Briefing refreshed",
        "generated_at": result["generated_at"],
    }


@router.post("/refresh-prices")
async def refresh_prices() -> dict:
    """
    Lightweight refresh: re-fetch indices, FX, and holding prices, then patch the
    latest briefing snapshot in place. Does NOT regenerate news / analyst / AI synthesis.

    Called on every app open so market data always reflects the current or last close.
    Runs in a thread pool — refresh_prices_only() is synchronous yfinance I/O.
    """
    orchestrator = BriefingOrchestrator(settings.DB_PATH)
    await asyncio.to_thread(orchestrator.refresh_prices_only)

    return {"status": "Prices refreshed"}
