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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from backend.core.data_fetcher import DataFetcher
from backend.core.portfolio import batch_compute_daily_pct, get_portfolio_with_pl
from backend.core.ai_synthesis import synthesise_holdings
from backend.core.alert_evaluator import evaluate_alerts

logger = logging.getLogger(__name__)

_IST = ZoneInfo("Asia/Kolkata")
_ORCHESTRATION_LOCK = threading.RLock()


def _run_parallel(tasks: dict[str, Callable], max_workers: int = 4) -> dict[str, object]:
    """Run independent I/O-bound callables in parallel; failures become None."""
    if not tasks:
        return {}
    workers = min(max_workers, len(tasks))
    results: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                logger.warning("BriefingOrchestrator: parallel task %s failed: %s", key, exc)
                results[key] = None
    return results


def _load_holding_tickers(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT ticker_yfinance FROM holdings WHERE ticker_yfinance IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows if r[0]]


def _enrich_holdings_daily_pct(db_path: str, portfolio_data: dict) -> None:
    """Attach daily_pct / day_change / day_change_pct to each holding in-place."""
    holdings = portfolio_data.get("holdings", [])
    tickers = [
        h.get("ticker_yfinance") or h.get("ticker")
        for h in holdings
    ]
    pct_map = batch_compute_daily_pct(db_path, tickers)
    for holding, ticker in zip(holdings, tickers):
        if not ticker:
            holding["daily_pct"] = None
            holding["day_change"] = None
            holding["day_change_pct"] = None
            continue
        pct = pct_map.get(ticker)
        holding["daily_pct"] = pct
        holding["day_change_pct"] = round(pct, 2) if pct is not None else None
        if pct is not None and holding.get("current_price") is not None:
            units = holding.get("quantity") or holding.get("units") or 0
            price_change = holding["current_price"] * pct / (100 + pct)
            holding["day_change"] = round(price_change * units, 2)
        else:
            holding["day_change"] = None


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
        """Generate a briefing while serializing with other refresh/generate runs."""
        with _ORCHESTRATION_LOCK:
            return self._generate()

    def _generate(self) -> dict:
        """
        Generate a new briefing by fetching all data sources and storing to DB.

        Steps:
          1. Fetch EUR/INR FX rate (used for portfolio P&L conversion)
          2. Fetch market indices
          3. Compute portfolio P&L
          4. Fetch technical signals (RSI/MACD/SMA) and merge into holdings
          5. Fetch news (holdings + India/Germany/US macro tabs)
          6. Fetch analyst consensus ratings from Finnhub
          7. AI synthesis — enrich holdings with rec + ai_narrative via Claude Haiku 4.5
          8. Assemble briefing dict
          9. INSERT into briefing_snapshots
          10. Return briefing dict

        Exceptions in individual sections are caught and logged — partial data
        is better than no briefing (fail-open per T-04-04 guidance).
        """
        holding_tickers = _load_holding_tickers(self.db_path)

        # Phase 1 — independent market fetches in parallel (FX, indices, holding prices)
        phase1_tasks: dict[str, Callable] = {
            "fx_eur": lambda: self.fetcher.fetch_fx_rate(),
            "fx_usd": lambda: self.fetcher.fetch_fx_rate("USDINR=X"),
            "indices": lambda: self.fetcher.fetch_indices(),
        }
        if holding_tickers:
            phase1_tasks["holding_prices"] = lambda: self.fetcher.fetch_holding_prices(holding_tickers)
        phase1 = _run_parallel(phase1_tasks, max_workers=4)

        fx_data = phase1.get("fx_eur") or {}
        if not isinstance(fx_data, dict):
            fx_data = {}
        fx_rate_eurinr = fx_data.get("rate", 90.0)

        usdinr_data = phase1.get("fx_usd") or {}
        if not isinstance(usdinr_data, dict):
            usdinr_data = {}
        fx_rate_usdinr = usdinr_data.get("rate", 83.0)

        indices_data = phase1.get("indices") or {}
        if not isinstance(indices_data, dict):
            indices_data = {}

        try:
            portfolio_data = get_portfolio_with_pl(
                self.db_path,
                fx_rate_eurinr=fx_rate_eurinr,
                fx_rate_usdinr=fx_rate_usdinr,
            )
        except Exception as exc:
            logger.error("BriefingOrchestrator: portfolio fetch failed: %s", exc)
            portfolio_data = {}

        # Enrich holdings with daily_pct / day_change / day_change_pct (single DB query)
        try:
            _enrich_holdings_daily_pct(self.db_path, portfolio_data)
        except Exception as exc:
            logger.warning("BriefingOrchestrator: daily_pct enrichment failed: %s", exc)
            for holding in portfolio_data.get("holdings", []):
                holding.setdefault("daily_pct", None)
                holding.setdefault("day_change", None)
                holding.setdefault("day_change_pct", None)

        signal_tickers = [
            h["ticker_yfinance"]
            for h in portfolio_data.get("holdings", [])
            if h.get("ticker_yfinance")
        ]
        holding_names = [h.get("name", h["ticker"]) for h in portfolio_data.get("holdings", [])]

        # Phase 2 — signals, news, analyst, benchmark are independent after portfolio is ready
        phase2_tasks: dict[str, Callable] = {}
        if signal_tickers:
            phase2_tasks["signals"] = lambda: self.fetcher.fetch_signals(signal_tickers)
        phase2_tasks["news"] = lambda: self.fetcher.fetch_news(holding_tickers, holding_names)
        phase2_tasks["analyst"] = lambda: self.fetcher.fetch_analyst(holding_tickers)
        phase2_tasks["benchmark"] = lambda: self.fetcher.fetch_benchmark(
            portfolio_data.get("holdings", [])
        )
        phase2 = _run_parallel(phase2_tasks, max_workers=4)

        signals_data = phase2.get("signals") or {}
        if not isinstance(signals_data, dict):
            signals_data = {}

        news_data = phase2.get("news")
        if not isinstance(news_data, dict) or "holdings" not in news_data:
            news_data = {"holdings": [], "india": [], "germany": [], "us": []}

        analyst_data = phase2.get("analyst") or {}
        if not isinstance(analyst_data, dict):
            analyst_data = {}

        benchmark_data = phase2.get("benchmark") or {}
        if not isinstance(benchmark_data, dict):
            benchmark_data = {}

        # Merge signals into each holding dict — keyed by ticker_yfinance
        for holding in portfolio_data.get("holdings", []):
            yf_ticker = holding.get("ticker_yfinance")
            sig = signals_data.get(yf_ticker, {}) if yf_ticker else {}
            holding["rsi_14"] = sig.get("rsi_14", None)
            holding["macd"] = sig.get("macd", None)
            holding["macd_signal"] = sig.get("macd_signal", None)
            holding["macd_histogram"] = sig.get("macd_histogram", None)
            holding["sma_50"] = sig.get("sma_50", None)
            holding["sma_200"] = sig.get("sma_200", None)

        # Alert evaluation — runs after analyst (analyst-change detection needs analyst_curr)
        try:
            alert_settings = self._load_alert_settings()
            analyst_prev = self._load_yesterday_analyst()
            analyst_curr_map = analyst_data or {}
            alerts_fired = evaluate_alerts(
                portfolio_data.get("holdings", []),
                signals_data or {},
                analyst_prev,
                analyst_curr_map,
                alert_settings,
            )
        except Exception as exc:
            logger.error("BriefingOrchestrator: alert evaluation failed: %s", exc)
            alerts_fired = []

        # Step 7 — AI synthesis: enrich holdings with rec + ai_narrative via Claude Haiku 4.5
        try:
            cash_by_broker = portfolio_data.get("cash_by_broker", {})
            enriched = synthesise_holdings(portfolio_data, signals_data, analyst_data, cash_by_broker)
            portfolio_data["holdings"] = enriched
        except Exception as exc:
            logger.error("BriefingOrchestrator: AI synthesis failed: %s", exc)
            # holdings remain with signals already merged from step 4; rec/ai_narrative will be None

        # Step 7.5: Benchmark comparison — already fetched in Phase 2, reuse it

        # Step 8: Assemble briefing
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(_IST)
        briefing_date = now_ist.strftime("%Y-%m-%d")
        generated_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        briefing = {
            "portfolio": portfolio_data,
            "benchmark_data": benchmark_data,
            "indices": indices_data,
            "fx": fx_data,
            "news": news_data,
            "alerts_fired": alerts_fired,
            "generated_at": generated_at,
            "briefing_date": briefing_date,
        }

        # Step 9: INSERT into briefing_snapshots, then prune old rows (keep last 30)
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

    # ---------------------------------------------------------------------------
    # Alert helpers
    # ---------------------------------------------------------------------------

    def _load_alert_settings(self) -> dict:
        """
        Read all alert_* keys from the settings table.

        Returns a dict of {key: value} for keys starting with 'alert_'.
        Returns {} on any error.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        finally:
            conn.close()
        return {k: v for k, v in rows if k.startswith("alert_")}

    def _load_yesterday_analyst(self) -> dict:
        """
        Query analyst_cache for the most recent date strictly before today.

        Returns a dict keyed by symbol: {"rating": str, "target": float}.
        Returns {} on any error or if no historical data exists.
        """
        from datetime import date as _date
        today_str = _date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT symbol, rating, target_mean
                    FROM analyst_cache
                    WHERE date = (
                        SELECT MAX(date) FROM analyst_cache WHERE date < ?
                    )
                    """,
                    (today_str,),
                ).fetchall()
            finally:
                conn.close()
            return {
                row[0]: {"rating": row[1], "target": row[2]}
                for row in rows
                if row[0]
            }
        except Exception as exc:
            logger.warning("BriefingOrchestrator: _load_yesterday_analyst failed: %s", exc)
            return {}

    def refresh_prices_only(self) -> None:
        """Refresh prices while serializing with other refresh/generate runs."""
        with _ORCHESTRATION_LOCK:
            return self._refresh_prices_only()

    def _refresh_prices_only(self) -> None:
        """
        Fetch fresh prices/FX/indices and patch the latest briefing snapshot in-place.
        Called on every app startup so the portfolio always shows current or last-close prices.
        Does NOT regenerate news, analyst ratings, or AI narratives.
        """
        # Load holding tickers first (fast SQL)
        holding_tickers = _load_holding_tickers(self.db_path)

        # Phase 1: FX, indices, holding prices are independent I/O — run in parallel
        refresh_tasks: dict[str, Callable] = {
            "fx_eur": lambda: self.fetcher.fetch_fx_rate(),
            "fx_usd": lambda: self.fetcher.fetch_fx_rate("USDINR=X"),
            "indices": lambda: self.fetcher.fetch_indices(),
        }
        if holding_tickers:
            refresh_tasks["holding_prices"] = lambda: self.fetcher.fetch_holding_prices(holding_tickers)
        refresh_results = _run_parallel(refresh_tasks, max_workers=4)

        fx_data = refresh_results.get("fx_eur") or {}
        if not isinstance(fx_data, dict):
            fx_data = {}
        fx_rate_eurinr = fx_data.get("rate", 90.0)

        usdinr_data = refresh_results.get("fx_usd") or {}
        if not isinstance(usdinr_data, dict):
            usdinr_data = {}
        fx_rate_usdinr = usdinr_data.get("rate", 83.0)

        indices_data = refresh_results.get("indices") or {}
        if not isinstance(indices_data, dict):
            indices_data = None

        # Recompute portfolio P&L with fresh prices
        try:
            portfolio_data = get_portfolio_with_pl(
                self.db_path,
                fx_rate_eurinr=fx_rate_eurinr,
                fx_rate_usdinr=fx_rate_usdinr,
            )
        except Exception as exc:
            logger.warning("refresh_prices_only: portfolio P&L recompute failed: %s", exc)
            portfolio_data = None

        # Enrich holdings with daily_pct / day_change
        if portfolio_data:
            try:
                for holding in portfolio_data.get("holdings", []):
                    ticker = holding.get("ticker_yfinance") or holding.get("ticker")
                    if not ticker:
                        holding["daily_pct"] = None
                        holding["day_change"] = None
                        holding["day_change_pct"] = None
                    else:
                        pct = compute_daily_pct(self.db_path, ticker)
                        holding["daily_pct"] = pct
                        holding["day_change_pct"] = round(pct, 2) if pct is not None else None
                        if pct is not None and holding.get("current_price") is not None:
                            units = holding.get("quantity") or holding.get("units") or 0
                            price_change = holding["current_price"] * pct / (100 + pct)
                            holding["day_change"] = round(price_change * units, 2)
                        else:
                            holding["day_change"] = None
            except Exception as exc:
                logger.warning("refresh_prices_only: daily_pct enrichment failed: %s", exc)

        # Patch the latest briefing snapshot
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id, briefing_json FROM briefing_snapshots ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if row:
                snap_id, snap_json = row
                try:
                    briefing = json.loads(snap_json)
                except Exception:
                    briefing = {}
                if portfolio_data is not None:
                    briefing["portfolio"] = portfolio_data
                if indices_data is not None:
                    briefing["indices"] = indices_data
                if fx_data:
                    briefing["fx"] = fx_data
                briefing["prices_refreshed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    "UPDATE briefing_snapshots SET briefing_json = ? WHERE id = ?",
                    (json.dumps(briefing), snap_id),
                )
                conn.commit()
                logger.info("refresh_prices_only: patched briefing snapshot id=%d", snap_id)
            else:
                # No existing snapshot — do a full generate instead
                logger.info("refresh_prices_only: no snapshot found, running full generate")
                self.generate()
        except Exception as exc:
            logger.warning("refresh_prices_only: failed to patch briefing snapshot: %s", exc)
        finally:
            conn.close()

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
