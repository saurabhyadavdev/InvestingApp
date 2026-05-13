"""
GET /api/briefing — returns the latest cached briefing from briefing_snapshots.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.briefing import BriefingOrchestrator

router = APIRouter(prefix="/api")


@router.get("/briefing")
async def get_briefing() -> dict:
    """
    Return the most recently generated briefing snapshot.

    Returns
    -------
    dict
        Parsed briefing JSON with keys: portfolio, indices, fx, generated_at,
        briefing_date, fetched_at.

    Raises
    ------
    HTTPException 404
        If no briefing has been generated yet (briefing_snapshots is empty).
    """
    orchestrator = BriefingOrchestrator(settings.DB_PATH)
    latest = orchestrator.get_latest()

    if latest is None:
        raise HTTPException(status_code=404, detail="No briefing generated yet")

    # Add fetched_at timestamp (time this request was served, not when generated)
    latest["fetched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return latest
