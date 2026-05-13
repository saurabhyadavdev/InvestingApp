"""
GET /api/fx     — return EUR/INR rate + 24h range + alert threshold.
POST /api/fx/alert — set EUR/INR alert threshold persisted in settings table.

Security:
  T-03-01 — Pydantic validates threshold > 0 (FXAlertRequest); parameterized INSERT.
  T-03-05 — Only "fx_alert_threshold" key is written — hardcoded string, not user input.
"""
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.data_fetcher import DataFetcher
from backend.models import FXAlertRequest, FXAlertResponse, FXResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["fx"])

_SETTINGS_KEY = "fx_alert_threshold"


@router.get("/fx", response_model=FXResponse)
async def get_fx():
    """
    Return current EUR/INR rate, 24h low/high, timestamp, and alert threshold.

    Response
    --------
    {
      "pair": "EURINR",
      "rate": 98.45,
      "low": 97.80,
      "high": 99.10,
      "timestamp": "<UTC ISO 8601>",
      "alert_threshold": 99.5   // null if not set
    }
    """
    fetcher = DataFetcher(settings.DB_PATH)
    try:
        fx_data = fetcher.fetch_fx_rate("EURINR=X")
    except Exception as exc:
        logger.warning("fetch_fx_rate failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"FX data unavailable — {datetime.now(timezone.utc).isoformat()}. Retry in 1 minute.",
        )

    # Read alert threshold from settings table
    alert_threshold = _get_alert_threshold(settings.DB_PATH)

    # T-06-01: alert_triggered computed server-side — frontend receives bool, not raw comparison
    alert_triggered = bool(alert_threshold is not None and fx_data["rate"] >= alert_threshold)

    return FXResponse(
        pair=fx_data["pair"],
        rate=fx_data["rate"],
        low=fx_data["low"],
        high=fx_data["high"],
        timestamp=fx_data["timestamp"],
        alert_threshold=alert_threshold,
        alert_triggered=alert_triggered,
    )


@router.post("/fx/alert", response_model=FXAlertResponse)
async def set_fx_alert(body: FXAlertRequest):
    """
    Persist EUR/INR alert threshold to settings table.

    Validates threshold > 0 (T-03-01 mitigation).
    Writes to settings table with key="fx_alert_threshold" (T-03-05 mitigation).
    """
    if body.threshold <= 0:
        raise HTTPException(status_code=422, detail="Threshold must be a positive number")

    _save_alert_threshold(settings.DB_PATH, body.threshold)

    return FXAlertResponse(
        alert_threshold=body.threshold,
        message="Alert threshold set",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_alert_threshold(db_path: str) -> Optional[float]:
    """Read fx_alert_threshold from settings table; return None if not set."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT value FROM settings WHERE key = ?",
            (_SETTINGS_KEY,),
        )
        row = cursor.fetchone()
        if row:
            try:
                return float(row[0])
            except (ValueError, TypeError):
                return None
        return None
    finally:
        conn.close()


def _save_alert_threshold(db_path: str, threshold: float) -> None:
    """Persist fx_alert_threshold to settings table with parameterized INSERT OR REPLACE."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (_SETTINGS_KEY, str(threshold)),
        )
        conn.commit()
    finally:
        conn.close()
