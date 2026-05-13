"""
BriefingOrchestrator: aggregates portfolio + indices + FX data into a single briefing.

Stores results to briefing_snapshots table for caching.
Called by APScheduler at 07:00 IST and on-demand via POST /api/refresh.

Security note (T-04-03):
  - Uses json.loads() only — never eval()
  - All SQL uses parameterized ? placeholders — no f-string SQL
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from backend.core.data_fetcher import DataFetcher
from backend.core.portfolio import get_portfolio_with_pl

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")


class BriefingOrchestrator:
    """
    Orchestrates daily briefing generation by aggregating:
      - Portfolio P&L (from holdings + price_history)
      - Market indices (from yfinance via DataFetcher)
      - EUR/INR FX rate (from yfinance via DataFetcher)

    Results are stored in briefing_snapshots for serving via GET /api/briefing.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.fetcher = DataFetcher(db_path)

    def generate(self) -> dict:
        """
        Generate a new briefing by fetching all data sources and storing to DB.

        Steps:
          1. Fetch EUR/INR FX rate (used for portfolio P&L conversion)
          2. Fetch market indices
          3. Compute portfolio P&L
          4. Assemble briefing dict
          5. INSERT into briefing_snapshots
          6. Return briefing dict

        Exceptions in individual sections are caught and logged — partial data
        is better than no briefing (fail-open per T-04-04 guidance).
        """
        # Step 1: FX rates (needed for portfolio P&L conversion)
        try:
            fx_data = self.fetcher.fetch_fx_rate()
            fx_rate_eurinr = fx_data.get("rate", 90.0)
        except Exception as exc:
            logger.error("BriefingOrchestrator: FX fetch failed: %s", exc)
            fx_data = {}
            fx_rate_eurinr = 90.0

        # Fetch USD/INR rate separately (T-05-02: wrapped in try/except, default 83.0 on failure)
        try:
            usdinr_data = self.fetcher.fetch_fx_rate("USDINR=X")
            fx_rate_usdinr = usdinr_data.get("rate", 83.0)
        except Exception as exc:
            logger.error("BriefingOrchestrator: USDINR FX fetch failed: %s", exc)
            fx_rate_usdinr = 83.0

        # Step 2: Market indices
        try:
            indices_data = self.fetcher.fetch_indices()
        except Exception as exc:
            logger.error("BriefingOrchestrator: indices fetch failed: %s", exc)
            indices_data = {}

        # Step 3: Portfolio P&L
        try:
            portfolio_data = get_portfolio_with_pl(
                self.db_path,
                fx_rate_eurinr=fx_rate_eurinr,
                fx_rate_usdinr=fx_rate_usdinr,
            )
        except Exception as exc:
            logger.error("BriefingOrchestrator: portfolio fetch failed: %s", exc)
            portfolio_data = {}

        # Step 4: Assemble briefing
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(_IST)
        briefing_date = now_ist.strftime("%Y-%m-%d")
        generated_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        briefing = {
            "portfolio": portfolio_data,
            "indices": indices_data,
            "fx": fx_data,
            "generated_at": generated_at,
            "briefing_date": briefing_date,
        }

        # Step 5: INSERT into briefing_snapshots, then prune old rows (keep last 30)
        try:
            briefing_json = json.dumps(briefing)
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute(
                    "INSERT INTO briefing_snapshots (date, type, briefing_json) VALUES (?, ?, ?)",
                    (briefing_date, "morning", briefing_json),
                )
                # Delete all but the most recent 30 rows to prevent unbounded growth
                conn.execute("""
                    DELETE FROM briefing_snapshots
                    WHERE id NOT IN (
                        SELECT id FROM briefing_snapshots ORDER BY created_at DESC LIMIT 30
                    )
                """)
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.error("BriefingOrchestrator: failed to store briefing: %s", exc)

        return briefing

    def get_latest(self) -> Optional[dict]:
        """
        Return the most recently generated briefing as a dict, or None if empty.

        Uses json.loads() — never eval() (T-04-03 mitigation).
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT briefing_json FROM briefing_snapshots ORDER BY created_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if row is None:
            return None

        try:
            return json.loads(row[0])
        except Exception as exc:
            logger.error("BriefingOrchestrator: failed to parse briefing JSON: %s", exc)
            return None
