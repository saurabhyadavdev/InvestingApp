"""
POST /api/alerts  — save alert configuration to the settings table.
GET  /api/alerts  — read alert configuration from the settings table.

Security:
  - Only keys in the alert_* namespace are written — fx_alert_threshold is never touched.
  - All SQL uses parameterized ? placeholders — no f-string SQL for values.
  - Never bulk-deletes from settings; uses INSERT OR REPLACE per individual key.
  - Response is always JSON — never raises HTTP 500.
"""
import logging
import sqlite3
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings as config_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["alerts"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AlertSettings(BaseModel):
    price_targets: dict[str, float] = {}
    price_enabled: dict[str, bool] = {}
    daily_move_pct: Optional[float] = 5.0
    daily_move_enabled: bool = False
    rsi_enabled: bool = False
    analyst_enabled: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/alerts")
async def save_alerts(payload: AlertSettings) -> dict:
    """
    Persist alert configuration to the settings table.

    Each field maps to one or more alert_* keys:
      - price_targets: {ticker → target}   → alert_price_{ticker}
      - price_enabled: {ticker → bool}     → alert_price_{ticker}_enabled
      - daily_move_pct: float              → alert_daily_move_pct
      - daily_move_enabled: bool           → alert_daily_move_enabled
      - rsi_enabled: bool                  → alert_rsi_enabled
      - analyst_enabled: bool              → alert_analyst_enabled

    fx_alert_threshold is NEVER read or written by this endpoint.
    """
    try:
        conn = sqlite3.connect(config_settings.DB_PATH)
        try:
            # Price targets (per ticker)
            for ticker, target in (payload.price_targets or {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (f"alert_price_{ticker}", str(target)),
                )

            # Price enabled flags (per ticker)
            for ticker, enabled in (payload.price_enabled or {}).items():
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (f"alert_price_{ticker}_enabled", "true" if enabled else "false"),
                )

            # Daily move threshold (global)
            if payload.daily_move_pct is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("alert_daily_move_pct", str(payload.daily_move_pct)),
                )

            # Daily move enabled (global)
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("alert_daily_move_enabled", "true" if payload.daily_move_enabled else "false"),
            )

            # RSI alerts enabled (global)
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("alert_rsi_enabled", "true" if payload.rsi_enabled else "false"),
            )

            # Analyst alerts enabled (global)
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("alert_analyst_enabled", "true" if payload.analyst_enabled else "false"),
            )

            conn.commit()
        finally:
            conn.close()

        return {"ok": True}

    except Exception as exc:
        logger.error("POST /api/alerts failed: %s", exc)
        return {"ok": False, "error": str(exc)}


@router.get("/alerts")
async def get_alerts() -> dict:
    """
    Read alert configuration from the settings table and return in the same
    shape as the POST body.

    fx_alert_threshold MUST NOT appear in the response.
    """
    try:
        conn = sqlite3.connect(config_settings.DB_PATH)
        try:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'alert_%'"
            ).fetchall()
        finally:
            conn.close()

        # Build settings dict from alert_* rows only
        settings_map = {k: v for k, v in rows if k.startswith("alert_")}

        # Reconstruct price_targets and price_enabled dicts
        price_targets: dict = {}
        price_enabled: dict = {}

        for key, value in settings_map.items():
            if key.startswith("alert_price_") and key.endswith("_enabled"):
                ticker = key[len("alert_price_"):-len("_enabled")]
                price_enabled[ticker] = value == "true"
            elif key.startswith("alert_price_"):
                ticker = key[len("alert_price_"):]
                try:
                    price_targets[ticker] = float(value)
                except (ValueError, TypeError):
                    pass

        # Parse global numeric/bool settings
        daily_move_pct_raw = settings_map.get("alert_daily_move_pct")
        try:
            daily_move_pct = float(daily_move_pct_raw) if daily_move_pct_raw is not None else 5.0
        except (ValueError, TypeError):
            daily_move_pct = 5.0

        daily_move_enabled = settings_map.get("alert_daily_move_enabled") == "true"
        rsi_enabled = settings_map.get("alert_rsi_enabled") == "true"
        analyst_enabled = settings_map.get("alert_analyst_enabled") == "true"

        return {
            "price_targets": price_targets,
            "price_enabled": price_enabled,
            "daily_move_pct": daily_move_pct,
            "daily_move_enabled": daily_move_enabled,
            "rsi_enabled": rsi_enabled,
            "analyst_enabled": analyst_enabled,
        }

    except Exception as exc:
        logger.error("GET /api/alerts failed: %s", exc)
        return {
            "price_targets": {},
            "price_enabled": {},
            "daily_move_pct": 5.0,
            "daily_move_enabled": False,
            "rsi_enabled": False,
            "analyst_enabled": False,
        }
