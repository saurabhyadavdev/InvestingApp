"""
GET /api/briefing — returns the latest cached briefing from briefing_snapshots.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.briefing import BriefingOrchestrator

router = APIRouter(prefix="/api")

_ALERT_KEY = "fx_alert_threshold"


def _get_alert_threshold(db_path: str) -> Optional[float]:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (_ALERT_KEY,)
        ).fetchone()
        return float(row[0]) if row else None
    except (ValueError, TypeError):
        return None
    finally:
        conn.close()


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

    # Inject live alert state into fx section — snapshot doesn't include it
    alert_threshold = _get_alert_threshold(settings.DB_PATH)
    if isinstance(latest.get("fx"), dict):
        fx_rate = latest["fx"].get("rate")
        latest["fx"]["alert_threshold"] = alert_threshold
        latest["fx"]["alert_triggered"] = bool(
            alert_threshold is not None
            and fx_rate is not None
            and fx_rate >= alert_threshold
        )

    # Add fetched_at timestamp (time this request was served, not when generated)
    latest["fetched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return latest
