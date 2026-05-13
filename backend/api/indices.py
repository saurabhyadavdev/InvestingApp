"""
GET /api/indices — return Nifty 50, Sensex, DAX, S&P 500 with close, change_pct, date, market_label.

Fallback: if DataFetcher raises, serve cached data from price_history table.
If neither succeeds, return 503 with actionable message (UI-SPEC copy).

Security: T-03-04 — cache fallback prevents excessive yfinance retries on failure.
"""
import sqlite3
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.core.data_fetcher import DataFetcher, _INDEX_META

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["indices"])

# Canonical order for display
_SYMBOL_ORDER = ["^NSEI", "^BSESN", "^GDAXI", "^GSPC", "^NDX"]


@router.get("/indices")
async def get_indices():
    """
    Return the 5 major market indices with closing prices and % change.

    Response
    --------
    {
      "indices": [
        {"symbol": "^NSEI", "name": "Nifty 50", "close": 23456.78,
         "change_pct": 1.2, "date": "2026-05-12", "market_label": "Nifty 50"},
        ...
      ],
      "fetched_at": "<UTC ISO 8601>"
    }
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Attempt live fetch
    try:
        fetcher = DataFetcher(settings.DB_PATH)
        data = fetcher.fetch_indices()
        if data:
            indices_list = [
                {
                    "symbol": sym,
                    "name": v["name"],
                    "close": v["close"],
                    "change_pct": v["change_pct"],
                    "date": v["date"],
                    "market_label": v["market_label"],
                }
                for sym in _SYMBOL_ORDER
                for v in [data[sym]]
                if sym in data
            ]
            return {"indices": indices_list, "fetched_at": fetched_at}
    except Exception as exc:
        logger.warning("DataFetcher.fetch_indices() failed: %s", exc)

    # Cache fallback: serve last known close per index from price_history
    try:
        cached = _load_cached_indices(settings.DB_PATH)
        if cached:
            return {"indices": cached, "fetched_at": fetched_at, "from_cache": True}
    except Exception as exc:
        logger.warning("Cache fallback failed: %s", exc)

    # Neither live nor cache succeeded
    raise HTTPException(
        status_code=503,
        detail=f"Market data unavailable — {fetched_at}. Last updated: unknown. Retry in 1 minute.",
    )


def _load_cached_indices(db_path: str) -> list:
    """Load the most recent cached close per index from price_history."""
    results = []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        for symbol in _SYMBOL_ORDER:
            meta = _INDEX_META.get(symbol, {})
            cursor.execute(
                """
                SELECT close, date FROM price_history
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (symbol,),
            )
            row = cursor.fetchone()
            if row and row["close"] is not None:
                results.append(
                    {
                        "symbol": symbol,
                        "name": meta.get("name", symbol),
                        "close": float(row["close"]),
                        "change_pct": 0.0,  # Cannot compute without two rows
                        "date": row["date"],
                        "market_label": meta.get("name", symbol),
                    }
                )
    finally:
        conn.close()
    return results
