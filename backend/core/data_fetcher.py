"""
DataFetcher: fetch market indices and EUR/INR FX rate via yfinance.

Caches results to SQLite price_history and fx_rates tables.
Handles missing tickers gracefully (logs warning, continues).
Uses timezone-aware reference dates per market.

Security note (T-03-02, T-03-04):
  - All SQL uses parameterized ? placeholders — no f-string SQL.
  - Results cached with INSERT OR REPLACE; stale data served if yfinance fails.
"""
import logging
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import yfinance as yf

from backend.core.timezone_utils import get_market_reference_date

logger = logging.getLogger(__name__)

# Index metadata
_INDEX_META: dict = {
    "^NSEI":  {"name": "Nifty 50",  "market": "NSE"},
    "^BSESN": {"name": "Sensex",    "market": "NSE"},
    "^GDAXI": {"name": "DAX",       "market": "XETRA"},
    "^GSPC":  {"name": "S&P 500",   "market": "NYSE"},
}

_INDICES = list(_INDEX_META.keys())


class DataFetcher:
    """Fetch market data from yfinance and cache results to SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_indices(self) -> dict[str, dict]:
        """
        Fetch closing prices and % change for the 4 major indices.

        Returns
        -------
        dict
            Keyed by ticker symbol.  Each value is a dict with keys:
              close (float), change_pct (float), date (str YYYY-MM-DD),
              market_label (str), symbol (str), name (str).

        Behaviour
        ---------
        - Uses yf.download(threads=True) for parallel fetching.
        - Sorts the per-symbol DataFrame ascending before slicing so
          iloc[-1] = most recent, iloc[-2] = previous session.
        - Missing or errored tickers are skipped with a warning.
        - All successful results are cached to price_history via
          INSERT OR REPLACE with ? placeholders (T-03-02).
        """
        try:
            raw = yf.download(
                tickers=" ".join(_INDICES),
                period="5d",
                interval="1d",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            logger.warning("yfinance.download raised: %s", exc)
            return {}

        if raw is None or raw.empty:
            logger.warning("yfinance.download returned empty DataFrame")
            return {}

        results: dict[str, dict] = {}
        conn = sqlite3.connect(self.db_path)
        try:
            for symbol in _INDICES:
                meta = _INDEX_META[symbol]
                try:
                    # Extract single-symbol slice
                    if ("Close", symbol) in raw.columns:
                        # Multi-ticker layout: MultiIndex columns (Field, Ticker)
                        df_sym = raw.xs(symbol, axis=1, level=1)
                    elif "Close" in raw.columns:
                        # Single-ticker layout (shouldn't happen here but handle)
                        df_sym = raw
                    else:
                        logger.warning("No Close data for %s", symbol)
                        continue

                    df_sym = df_sym.sort_index(ascending=True).dropna(subset=["Close"])

                    if len(df_sym) < 2:
                        logger.warning("Insufficient rows for %s (need >= 2)", symbol)
                        continue

                    close_prev = float(df_sym["Close"].iloc[-2])
                    close_last = float(df_sym["Close"].iloc[-1])

                    if close_prev == 0:
                        logger.warning("Zero previous close for %s", symbol)
                        continue

                    change_pct = (close_last - close_prev) / close_prev * 100

                    # Use timezone-aware reference date for labelling
                    ref_date = get_market_reference_date(meta["market"])

                    entry: dict = {
                        "symbol": symbol,
                        "name": meta["name"],
                        "close": close_last,
                        "change_pct": round(change_pct, 4),
                        "date": ref_date,
                        "market_label": meta["name"],
                    }
                    results[symbol] = entry

                    # Cache to price_history (T-03-04)
                    self._cache_index_to_db(conn, symbol, df_sym)

                except Exception as exc:
                    logger.warning("Failed to process %s: %s", symbol, exc)
                    continue
        finally:
            conn.commit()
            conn.close()

        return results

    def fetch_fx_rate(self, pair: str = "EURINR=X") -> dict:
        """
        Fetch current EUR/INR rate from yfinance and cache to fx_rates.

        Parameters
        ----------
        pair : str
            yfinance ticker for the currency pair (default "EURINR=X").

        Returns
        -------
        dict
            Keys: pair (str), rate (float), low (float), high (float),
                  timestamp (str UTC ISO 8601).
        """
        ticker = yf.Ticker(pair)
        history = ticker.history(period="2d", interval="1d")

        if history.empty:
            raise ValueError(f"yfinance returned empty history for {pair}")

        history = history.sort_index(ascending=True)
        latest = history.iloc[-1]

        rate = float(latest["Close"])
        low = float(latest["Low"])
        high = float(latest["High"])

        # Timestamp: use the index value (tz-aware) → UTC ISO 8601
        raw_ts = history.index[-1]
        if hasattr(raw_ts, "tzinfo") and raw_ts.tzinfo is not None:
            ts_str = raw_ts.astimezone(timezone.utc).isoformat()
        else:
            ts_str = raw_ts.isoformat() + "Z"

        # Strip exchange-specific suffix to get canonical pair name
        canonical_pair = pair.replace("=X", "")

        result = {
            "pair": canonical_pair,
            "rate": rate,
            "low": low,
            "high": high,
            "timestamp": ts_str,
        }

        # Cache to fx_rates table
        self._cache_fx_to_db(canonical_pair, rate, low, high, ts_str)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _cache_index_to_db(self, conn: sqlite3.Connection, symbol: str, df) -> None:
        """Insert/replace price_history rows for *symbol* from *df*."""
        cursor = conn.cursor()
        for ts, row in df.iterrows():
            try:
                date_str = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO price_history
                        (ticker, date, open, high, low, close, adj_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        date_str,
                        float(row.get("Open", 0) or 0),
                        float(row.get("High", 0) or 0),
                        float(row.get("Low", 0) or 0),
                        float(row.get("Close", 0) or 0),
                        float(row.get("Adj Close", row.get("Close", 0)) or 0),
                        int(row.get("Volume", 0) or 0),
                    ),
                )
            except Exception as exc:
                logger.warning("Failed to cache row for %s: %s", symbol, exc)

    def _cache_fx_to_db(
        self,
        pair: str,
        rate: float,
        low: float,
        high: float,
        timestamp: str,
    ) -> None:
        """Insert/replace an fx_rates row."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO fx_rates (pair, rate, low, high, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pair, rate, low, high, timestamp),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("Failed to cache FX rate: %s", exc)
        finally:
            conn.close()
