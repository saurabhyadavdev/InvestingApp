"""
POST /api/refresh — triggers on-demand briefing regeneration.
"""
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.briefing import BriefingOrchestrator

router = APIRouter(prefix="/api")


@router.post("/refresh")
async def refresh_briefing() -> dict:
    """
    Trigger immediate briefing regeneration outside the scheduled window.

    Returns
    -------
    dict
        {"status": "Briefing refreshed", "generated_at": str}

    Note: No rate limiting in Phase 1 (T-04-01 accepted — single user local app).
    """
    orchestrator = BriefingOrchestrator(settings.DB_PATH)
    result = orchestrator.generate()

    return {
        "status": "Briefing refreshed",
        "generated_at": result["generated_at"],
    }
