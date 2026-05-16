"""
DataFetcher: fetch market indices and EUR/INR FX rate via yfinance.

Caches results to SQLite price_history and fx_rates tables.
Handles missing tickers gracefully (logs warning, continues).
Uses timezone-aware reference dates per market.

Security note (T-03-02, T-03-04):
  - All SQL uses parameterized ? placeholders — no f-string SQL.
  - Results cached with INSERT OR REPLACE; stale data served if yfinance fails.
"""
import json
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import finnhub
import ta
import yfinance as yf
from newsapi import NewsApiClient

from backend.config import settings
from backend.core.timezone_utils import get_market_reference_date

logger = logging.getLogger(__name__)

# Index metadata
_INDEX_META: dict = {
    "^NSEI":  {"name": "Nifty 50",    "market": "NSE"},
    "^BSESN": {"name": "Sensex",      "market": "NSE"},
    "^GDAXI": {"name": "DAX",         "market": "XETRA"},
    "^GSPC":  {"name": "S&P 500",     "market": "NYSE"},
    "^NDX":   {"name": "Nasdaq 100",  "market": "NASDAQ"},
}

_INDICES = list(_INDEX_META.keys())


# ---------------------------------------------------------------------------
# Module-level helpers (used by DataFetcher methods)
# ---------------------------------------------------------------------------

def _null_signals() -> dict:
    """Return a signals dict with all values set to None."""
    return {
        "rsi_14": None,
        "macd": None,
        "macd_signal": None,
        "macd_histogram": None,
        "sma_50": None,
        "sma_200": None,
    }


def _cache_signals(conn: sqlite3.Connection, ticker: str, today_str: str, sig: dict) -> None:
    """INSERT OR REPLACE a technical_indicators row using parameterized ? placeholders."""
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO technical_indicators
                (ticker, date, rsi_14, macd, macd_signal, macd_histogram, sma_50, sma_200)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                today_str,
                sig["rsi_14"],
                sig["macd"],
                sig["macd_signal"],
                sig["macd_histogram"],
                sig["sma_50"],
                sig["sma_200"],
            ),
        )
    except Exception as exc:
        logger.warning("_cache_signals: DB write failed for %s: %s", ticker, exc)


def _format_time_ago(published_at_str: str) -> str:
    """
    Parse a NewsAPI ISO 8601 publishedAt string and return a human-readable
    relative time string: "Xm ago", "Xh ago", or "Xd ago".
    """
    if not published_at_str:
        return ""
    try:
        # NewsAPI format: "2024-01-15T10:30:00Z"
        pub_dt = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - pub_dt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 3600:
            minutes = max(1, total_seconds // 60)
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"
    except Exception:
        return ""


class DataFetcher:
    """Fetch market data from yfinance and cache results to SQLite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_indices(self) -> dict[str, dict]:
        """
        Fetch closing prices and % change for the 5 major indices.

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

                    # Use the actual last DataFrame row date — ground truth from yfinance.
                    # This avoids weekend/holiday skew from the timezone-computed reference.
                    ref_date = df_sym.index[-1].date().isoformat()

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

    def fetch_holding_prices(self, tickers: list[str]) -> dict[str, float]:
        """
        Fetch latest closing prices for portfolio holdings and cache to price_history.

        Parameters
        ----------
        tickers : list[str]
            yfinance ticker symbols (e.g. ["AAVAS.NS", "SAP.DE"]).
            None/empty entries are skipped.

        Returns
        -------
        dict
            Keyed by ticker, value is latest close price (float).
            Tickers that fail silently are omitted from the result.
        """
        valid = [t for t in tickers if t]
        if not valid:
            return {}

        # Batch download — period="5d" catches recent trading days across timezones
        try:
            raw = yf.download(
                tickers=" ".join(valid),
                period="5d",
                interval="1d",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            logger.warning("fetch_holding_prices: yfinance.download raised: %s", exc)
            return {}

        if raw is None or raw.empty:
            logger.warning("fetch_holding_prices: yfinance returned empty DataFrame")
            return {}

        results: dict[str, float] = {}
        conn = sqlite3.connect(self.db_path)
        try:
            for ticker in valid:
                try:
                    # Handle single vs multi-ticker DataFrame layout
                    if ("Close", ticker) in raw.columns:
                        df_sym = raw.xs(ticker, axis=1, level=1)
                    elif len(valid) == 1 and "Close" in raw.columns:
                        df_sym = raw
                    else:
                        logger.warning("fetch_holding_prices: no Close data for %s", ticker)
                        continue

                    df_sym = df_sym.sort_index(ascending=True).dropna(subset=["Close"])
                    if df_sym.empty:
                        continue

                    close = float(df_sym["Close"].iloc[-1])
                    results[ticker] = close
                    self._cache_index_to_db(conn, ticker, df_sym)

                except Exception as exc:
                    logger.warning("fetch_holding_prices: failed for %s: %s", ticker, exc)
                    continue
        finally:
            conn.commit()
            conn.close()

        logger.info("fetch_holding_prices: fetched %d/%d tickers", len(results), len(valid))
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

    def fetch_signals(self, tickers: list) -> dict:
        """
        Compute RSI-14, MACD, SMA50, SMA200 for each ticker using 6 months of OHLCV data.

        Parameters
        ----------
        tickers : list[str]
            yfinance ticker symbols.

        Returns
        -------
        dict
            Keyed by ticker. Each value is a dict with keys:
              rsi_14, macd, macd_signal, macd_histogram, sma_50, sma_200 (float or None).

        Behaviour
        ---------
        - Batch-downloads 6mo OHLCV via yf.download (same pattern as fetch_indices).
        - Tickers with <15 close rows get all-None signals (no crash).
        - Tickers with >=15 but <200 rows get None only for indicators that need more rows.
        - Results cached to technical_indicators via INSERT OR REPLACE with ? placeholders (T-02-07).
        """
        valid = [t for t in tickers if t]
        if not valid:
            return {}

        try:
            raw = yf.download(
                tickers=" ".join(valid),
                period="6mo",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception as exc:
            logger.error("fetch_signals: yfinance.download raised: %s", exc)
            return {}

        if raw is None or raw.empty:
            logger.warning("fetch_signals: yfinance returned empty DataFrame")
            return {}

        results: dict = {}
        today_str = date.today().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            for ticker in valid:
                try:
                    # Extract single-symbol Close series — handle multi vs single layout
                    if ("Close", ticker) in raw.columns:
                        close_raw = raw.xs(ticker, axis=1, level=1)["Close"]
                    elif len(valid) == 1 and "Close" in raw.columns:
                        close_raw = raw["Close"]
                    else:
                        logger.warning("fetch_signals: no Close data for %s", ticker)
                        results[ticker] = _null_signals()
                        continue

                    close = close_raw.dropna()

                    if len(close) < 15:
                        logger.warning(
                            "fetch_signals: insufficient rows for %s (got %d, need >= 15)",
                            ticker, len(close),
                        )
                        results[ticker] = _null_signals()
                        _cache_signals(conn, ticker, today_str, _null_signals())
                        continue

                    sig = _null_signals()

                    # RSI-14
                    try:
                        rsi_val = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
                        sig["rsi_14"] = None if (rsi_val != rsi_val) else round(float(rsi_val), 2)
                    except Exception as exc:
                        logger.warning("fetch_signals: RSI failed for %s: %s", ticker, exc)

                    # MACD (needs >= 26 rows)
                    if len(close) >= 26:
                        try:
                            macd_obj = ta.trend.MACD(close=close)
                            macd_val = macd_obj.macd().iloc[-1]
                            signal_val = macd_obj.macd_signal().iloc[-1]
                            hist_val = macd_obj.macd_diff().iloc[-1]
                            sig["macd"] = None if (macd_val != macd_val) else round(float(macd_val), 4)
                            sig["macd_signal"] = None if (signal_val != signal_val) else round(float(signal_val), 4)
                            sig["macd_histogram"] = None if (hist_val != hist_val) else round(float(hist_val), 4)
                        except Exception as exc:
                            logger.warning("fetch_signals: MACD failed for %s: %s", ticker, exc)

                    # SMA-50 (needs >= 50 rows)
                    if len(close) >= 50:
                        try:
                            sma50_val = ta.trend.SMAIndicator(close=close, window=50).sma_indicator().iloc[-1]
                            sig["sma_50"] = None if (sma50_val != sma50_val) else round(float(sma50_val), 2)
                        except Exception as exc:
                            logger.warning("fetch_signals: SMA50 failed for %s: %s", ticker, exc)

                    # SMA-200 (needs >= 200 rows)
                    if len(close) >= 200:
                        try:
                            sma200_val = ta.trend.SMAIndicator(close=close, window=200).sma_indicator().iloc[-1]
                            sig["sma_200"] = None if (sma200_val != sma200_val) else round(float(sma200_val), 2)
                        except Exception as exc:
                            logger.warning("fetch_signals: SMA200 failed for %s: %s", ticker, exc)

                    results[ticker] = sig
                    _cache_signals(conn, ticker, today_str, sig)

                except Exception as exc:
                    logger.warning("fetch_signals: failed for %s: %s", ticker, exc)
                    continue
        finally:
            conn.commit()
            conn.close()

        logger.info("fetch_signals: computed signals for %d/%d tickers", len(results), len(valid))
        return results

    def fetch_news(self, tickers: list, holding_names: list) -> dict:
        """
        Fetch news headlines from NewsAPI for holdings and three macro themes.

        Parameters
        ----------
        tickers : list[str]
            yfinance ticker symbols (used for cache key derivation only).
        holding_names : list[str]
            Human-readable holding names used to build the holdings news query.

        Returns
        -------
        dict
            Keys: holdings (list), india (list), germany (list), us (list).
            Each list contains up to 5 article dicts:
              title (str), url (str), source (str), time_ago (str).

        Behaviour
        ---------
        - Returns empty lists for all tabs if NEWSAPI_KEY is unset.
        - Uses date-keyed cache in news_cache to prevent re-fetching same day's results.
        - Each NewsAPI call is individually wrapped in try/except (fail-open).
        - All SQL uses parameterized ? placeholders — no f-string SQL (T-02-05).
        """
        empty = {"holdings": [], "india": [], "germany": [], "us": []}

        if not settings.NEWSAPI_KEY:
            logger.warning("fetch_news: NEWSAPI_KEY not set — returning empty news")
            return empty

        today_str = date.today().isoformat()
        newsapi = NewsApiClient(api_key=settings.NEWSAPI_KEY)
        from_date = (date.today() - timedelta(days=2)).isoformat()

        # Build queries
        if holding_names:
            holdings_query = " OR ".join(holding_names[:3])
        else:
            holdings_query = " OR ".join(tickers[:3]) if tickers else "stocks"

        tab_queries = {
            "holdings": holdings_query,
            "india": "India economy OR RBI OR Nifty OR NSE OR budget India",
            "germany": "Germany economy OR ECB OR DAX OR Bundesbank OR euro zone",
            "us": "Federal Reserve OR S&P500 OR Nasdaq OR US stocks OR earnings",
        }

        result = {}
        conn = sqlite3.connect(self.db_path)
        try:
            for tab, query in tab_queries.items():
                # Check cache first
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT articles_json FROM news_cache WHERE query = ? AND date = ?",
                        (query, today_str),
                    )
                    cached_row = cursor.fetchone()
                    if cached_row:
                        result[tab] = json.loads(cached_row[0])
                        logger.info("fetch_news: cache hit for tab=%s", tab)
                        continue
                except Exception as exc:
                    logger.warning("fetch_news: cache read failed for tab=%s: %s", tab, exc)

                # Fetch from NewsAPI
                articles_list = []
                try:
                    response = newsapi.get_everything(
                        q=query,
                        from_param=from_date,
                        language="en",
                        sort_by="relevancy",
                        page_size=5,
                    )
                    articles = response.get("articles", []) or []
                    for article in articles[:5]:
                        articles_list.append({
                            "title": article.get("title", ""),
                            "url": article.get("url", ""),
                            "source": (article.get("source") or {}).get("name", ""),
                            "time_ago": _format_time_ago(article.get("publishedAt", "")),
                        })
                except Exception as exc:
                    logger.warning("fetch_news: NewsAPI call failed for tab=%s: %s", tab, exc)

                result[tab] = articles_list

                # Cache result
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO news_cache (query, date, articles_json) VALUES (?, ?, ?)",
                        (query, today_str, json.dumps(articles_list)),
                    )
                except Exception as exc:
                    logger.warning("fetch_news: cache write failed for tab=%s: %s", tab, exc)

            conn.commit()
        finally:
            conn.close()

        return result

    def fetch_analyst(self, tickers: list) -> dict:
        """
        Fetch analyst consensus ratings and price targets from Finnhub for each ticker.

        Parameters
        ----------
        tickers : list[str]
            yfinance ticker symbols (e.g. ["RELIANCE.NS", "SAP.DE", "AAPL"]).

        Returns
        -------
        dict
            Keyed by original yfinance ticker. Each value is a dict with:
              rating (str "BUY"|"HOLD"|"SELL" or None),
              target_mean (float or None),
              num_analysts (int or None).

        Behaviour
        ---------
        - Returns {} immediately if FINNHUB_KEY is empty (no crash).
        - Ticker translation: ".NS" → "NSE:<base>"; ".DE" → strip suffix; US pass-through.
        - Caches to analyst_cache via INSERT OR REPLACE with ? placeholders (T-02-16).
        - Each per-ticker Finnhub call is individually wrapped in try/except; continues.
        """
        if not settings.FINNHUB_KEY:
            logger.warning("fetch_analyst: FINNHUB_KEY not set — skipping analyst fetch")
            return {}

        client = finnhub.Client(api_key=settings.FINNHUB_KEY)
        today_str = date.today().isoformat()
        results: dict = {}
        conn = sqlite3.connect(self.db_path)
        try:
            for ticker in tickers:
                if not ticker:
                    continue
                try:
                    # Check analyst_cache first
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT rating, target_mean, num_analysts FROM analyst_cache WHERE symbol = ? AND date = ?",
                        (ticker, today_str),
                    )
                    cached_row = cursor.fetchone()
                    if cached_row:
                        results[ticker] = {
                            "rating": cached_row[0],
                            "target_mean": cached_row[1],
                            "num_analysts": cached_row[2],
                        }
                        logger.info("fetch_analyst: cache hit for %s", ticker)
                        continue

                    # Translate ticker to Finnhub symbol format
                    if ticker.endswith(".NS"):
                        finnhub_symbol = "NSE:" + ticker[:-3]
                    elif ticker.endswith(".DE"):
                        finnhub_symbol = ticker[:-3]
                    else:
                        finnhub_symbol = ticker

                    # Fetch recommendation trends
                    rating = None
                    try:
                        trends = client.recommendation_trends(finnhub_symbol)
                        if trends:
                            t = trends[0]
                            buy = (t.get("buy", 0) or 0) + (t.get("strongBuy", 0) or 0)
                            sell = (t.get("sell", 0) or 0) + (t.get("strongSell", 0) or 0)
                            hold = t.get("hold", 0) or 0
                            total = buy + sell + hold
                            if total > 0:
                                if buy / total > 0.5:
                                    rating = "BUY"
                                elif sell / total > 0.4:
                                    rating = "SELL"
                                else:
                                    rating = "HOLD"
                    except Exception as exc:
                        logger.warning("fetch_analyst: recommendation_trends failed for %s: %s", ticker, exc)

                    # Fetch price target
                    target_mean = None
                    num_analysts = None
                    try:
                        pt = client.price_target(finnhub_symbol)
                        target_mean = pt.get("targetMean")
                        num_analysts = pt.get("numberAnalysts")
                    except Exception as exc:
                        logger.warning("fetch_analyst: price_target failed for %s: %s", ticker, exc)

                    # Cache to analyst_cache
                    conn.execute(
                        "INSERT OR REPLACE INTO analyst_cache (symbol, date, rating, target_mean, num_analysts) VALUES (?, ?, ?, ?, ?)",
                        (ticker, today_str, rating, target_mean, num_analysts),
                    )

                    results[ticker] = {
                        "rating": rating,
                        "target_mean": target_mean,
                        "num_analysts": num_analysts,
                    }

                except Exception as exc:
                    logger.warning("fetch_analyst: failed for %s: %s", ticker, exc)
                    continue

            conn.commit()
        finally:
            conn.close()

        logger.info("fetch_analyst: fetched analyst data for %d/%d tickers", len(results), len(tickers))
        return results

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
        conn: sqlite3.Connection = None,
    ) -> None:
        """Insert/replace an fx_rates row.

        Parameters
        ----------
        conn : sqlite3.Connection, optional
            An existing open connection to reuse. If None, a new connection is
            opened and closed (with commit) within this call. Passing an existing
            connection avoids a second simultaneous write connection to the DB.
        """
        owns_conn = conn is None
        if owns_conn:
            conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO fx_rates (pair, rate, low, high, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (pair, rate, low, high, timestamp),
            )
            if owns_conn:
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to cache FX rate: %s", exc)
        finally:
            if owns_conn:
                conn.close()
