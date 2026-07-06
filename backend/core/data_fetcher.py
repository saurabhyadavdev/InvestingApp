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
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def _window_start(window: str) -> date:
    """Return the start date for a benchmark window.

    Parameters
    ----------
    window : str
        One of "1D", "1W", "1M", "3M", "YTD", "1Y".

    Raises
    ------
    ValueError
        If window is not one of the supported values.
    """
    today = date.today()
    if window == "1D":
        return today - timedelta(days=1)
    if window == "1W":
        return today - timedelta(days=7)
    if window == "1M":
        return today - timedelta(days=30)
    if window == "3M":
        return today - timedelta(days=90)
    if window == "YTD":
        return date(today.year, 1, 1)
    if window == "1Y":
        return today - timedelta(days=365)
    raise ValueError(f"Unknown window: {window}")


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


# Exchange timezones, for dating live-price overlays.
_TZ_KOLKATA = ZoneInfo("Asia/Kolkata")
_TZ_BERLIN = ZoneInfo("Europe/Berlin")
_TZ_NEWYORK = ZoneInfo("America/New_York")

# Map index market labels (from _INDEX_META) to their exchange timezone.
_MARKET_TZ: dict = {
    "NSE": _TZ_KOLKATA,
    "XETRA": _TZ_BERLIN,
    "NYSE": _TZ_NEWYORK,
    "NASDAQ": _TZ_NEWYORK,
}


def _exchange_tz(ticker: str) -> ZoneInfo:
    """Return the exchange timezone for a yfinance ticker suffix (defaults to US/Eastern)."""
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return _TZ_KOLKATA
    if ticker.endswith(".DE") or ticker.endswith(".F"):
        return _TZ_BERLIN
    return _TZ_NEWYORK


def _trading_day_in_tz(tz: ZoneInfo) -> str:
    """Return the current/most-recent trading-day date (YYYY-MM-DD) in *tz*.

    Unlike get_market_reference_date (most recently *closed* session), this returns
    today during an open or just-closed session, rolling back only over weekends.
    """
    local = datetime.now(timezone.utc).astimezone(tz)
    d = local.date()
    wd = d.weekday()  # Monday=0, Sunday=6
    if wd == 5:    # Saturday → Friday
        d -= timedelta(days=1)
    elif wd == 6:  # Sunday → Friday
        d -= timedelta(days=2)
    return d.isoformat()


def _current_session_date(ticker: str) -> str:
    """Current trading-day date in the ticker's exchange tz (for the holding overlay)."""
    return _trading_day_in_tz(_exchange_tz(ticker))


def _session_date_for_market(market: str) -> str:
    """Current trading-day date for an index market label (for the indices overlay)."""
    return _trading_day_in_tz(_MARKET_TZ.get(market, _TZ_NEWYORK))


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

        # Intraday batch: used as a fallback live overlay when the daily bar lags
        # and fast_info fails (notably some Yahoo index tickers such as Sensex).
        intraday_overlays: dict[str, dict] = {}
        try:
            intraday_raw = yf.download(
                tickers=" ".join(_INDICES),
                period="1d",
                interval="5m",
                progress=False,
                threads=True,
            )
            if intraday_raw is not None and not intraday_raw.empty:
                for sym in _INDICES:
                    try:
                        df_i = self._extract_symbol_frame(intraday_raw, sym, _INDICES)
                        if df_i is None:
                            continue
                        df_i = df_i.sort_index(ascending=True).dropna(subset=["Close"])
                        if not df_i.empty:
                            intraday_overlays[sym] = {
                                "date": df_i.index[-1].date().isoformat(),
                                "close": float(df_i["Close"].iloc[-1]),
                            }
                    except Exception:
                        continue
        except Exception as exc:
            logger.warning("fetch_indices: intraday session-date fetch failed: %s", exc)

        results: dict[str, dict] = {}
        conn = sqlite3.connect(self.db_path)
        try:
            # Pre-fetch fast_info for all indices in parallel (blocking network calls)
            fast_info_overlays: dict[str, dict] = {}
            def _fetch_fast_info(sym: str) -> tuple:
                try:
                    fast = yf.Ticker(sym).fast_info
                    try:
                        live_last = fast["lastPrice"]
                    except Exception:
                        live_last = getattr(fast, "last_price", None)
                    try:
                        live_prev = fast["previousClose"]
                    except Exception:
                        live_prev = getattr(fast, "previous_close", None)
                    if (
                        live_last is not None and live_last == live_last
                        and live_prev not in (None, 0) and live_prev == live_prev
                    ):
                        return sym, {"last": float(live_last), "prev": float(live_prev)}
                except Exception as exc:
                    logger.warning("fetch_indices: fast_info failed for %s: %s", sym, exc)
                return sym, None

            with ThreadPoolExecutor(max_workers=len(_INDICES)) as pool:
                for sym, info in pool.map(_fetch_fast_info, _INDICES):
                    if info is not None:
                        fast_info_overlays[sym] = info

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

                    intraday_overlay = intraday_overlays.get(symbol)

                    def apply_intraday_overlay() -> bool:
                        if not intraday_overlay:
                            return False
                        intraday_date = intraday_overlay.get("date")
                        intraday_close = intraday_overlay.get("close")
                        if (
                            not intraday_date
                            or intraday_date < ref_date
                            or intraday_close is None
                            or intraday_close != intraday_close
                        ):
                            return False

                        prev_for_change = close_last if intraday_date > ref_date else close_prev
                        if prev_for_change == 0:
                            return False

                        entry["close"] = float(intraday_close)
                        entry["change_pct"] = round(
                            (float(intraday_close) - prev_for_change) / prev_for_change * 100,
                            4,
                        )
                        entry["date"] = intraday_date
                        return True

                    # Use pre-fetched fast_info overlay (parallelized above)
                    fi = fast_info_overlays.get(symbol)
                    if fi is not None:
                        entry["close"] = fi["last"]
                        entry["change_pct"] = round((fi["last"] - fi["prev"]) / fi["prev"] * 100, 4)
                        entry["date"] = (
                            intraday_overlay.get("date") or _session_date_for_market(meta["market"])
                            if intraday_overlay
                            else _session_date_for_market(meta["market"])
                        )
                    else:
                        apply_intraday_overlay()

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
        Fetch latest prices for portfolio holdings and cache to price_history.

        Parameters
        ----------
        tickers : list[str]
            yfinance ticker symbols (e.g. ["AAVAS.NS", "SAP.DE"]).
            None/empty entries are skipped.

        Returns
        -------
        dict
            Keyed by ticker, value is latest available price (float).
            Tickers that fail silently are omitted from the result.
        """
        valid = [t for t in tickers if t]
        if not valid:
            return {}

        results: dict[str, float] = {}

        # Daily batch preserves recent history for daily change and fallback prices.
        daily_raw = None
        try:
            daily_raw = yf.download(
                tickers=" ".join(valid),
                period="5d",
                interval="1d",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            logger.warning("fetch_holding_prices: yfinance.download raised: %s", exc)
        if daily_raw is None or daily_raw.empty:
            logger.warning("fetch_holding_prices: yfinance returned empty DataFrame")

        conn = sqlite3.connect(self.db_path)
        try:
            if daily_raw is not None and not daily_raw.empty:
                for ticker in valid:
                    try:
                        df_sym = self._extract_symbol_frame(daily_raw, ticker, valid)
                        if df_sym is None:
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

            # Live-price overlay: replace today's close with the authoritative last
            # price from fast_info. The intraday 1m series' last bar is the
            # pre-auction tick (e.g. XETRA 17:29), which diverges from the official
            # close set by the closing auction; fast_info.last_price reflects the
            # auction and matches external sources. Dated to the current session so
            # it overlays — not overwrites — the previous daily close used for
            # day-change.
            #
            # Each fast_info read is a blocking network round-trip. Done serially
            # this dominates refresh latency (~0.3s × N tickers → ~20s for a
            # 70-holding portfolio), which is the bulk of the on-open wait. The
            # reads are independent and I/O-bound, so fan them out across a thread
            # pool; the per-ticker DB writes stay serial on this connection
            # (sqlite3 connections are not safe to share across threads).
            def _fetch_last_price(ticker: str):
                try:
                    fast = yf.Ticker(ticker).fast_info
                    try:
                        last_price = fast["lastPrice"]
                    except Exception:
                        last_price = getattr(fast, "last_price", None)
                    if last_price is None or last_price != last_price:  # None or NaN
                        return ticker, None
                    close = float(last_price)
                    if close <= 0:
                        return ticker, None
                    return ticker, close
                except Exception as exc:
                    logger.warning("fetch_holding_prices: fast_info failed for %s: %s", ticker, exc)
                    return ticker, None

            with ThreadPoolExecutor(max_workers=min(16, len(valid))) as pool:
                live_prices = list(pool.map(_fetch_last_price, valid))

            for ticker, close in live_prices:
                if close is None:
                    continue
                session_date = _current_session_date(ticker)
                results[ticker] = close
                self._cache_live_price_to_db(conn, ticker, session_date, close)
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
                period="1y",
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

        # Pre-extract Close series for all tickers (fast dict ops)
        close_series: dict[str, object] = {}
        for ticker in valid:
            try:
                if ("Close", ticker) in raw.columns:
                    close_raw = raw.xs(ticker, axis=1, level=1)["Close"]
                elif len(valid) == 1 and "Close" in raw.columns:
                    close_raw = raw["Close"]
                else:
                    logger.warning("fetch_signals: no Close data for %s", ticker)
                    continue
                close_series[ticker] = close_raw.dropna()
            except Exception as exc:
                logger.warning("fetch_signals: extract failed for %s: %s", ticker, exc)

        def _compute_one(ticker: str):
            close = close_series.get(ticker)
            if close is None or len(close) < 15:
                return ticker, _null_signals()

            sig = _null_signals()

            try:
                rsi_val = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
                sig["rsi_14"] = None if (rsi_val != rsi_val) else round(float(rsi_val), 2)
            except Exception as exc:
                logger.warning("fetch_signals: RSI failed for %s: %s", ticker, exc)

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

            if len(close) >= 50:
                try:
                    sma50_val = ta.trend.SMAIndicator(close=close, window=50).sma_indicator().iloc[-1]
                    sig["sma_50"] = None if (sma50_val != sma50_val) else round(float(sma50_val), 2)
                except Exception as exc:
                    logger.warning("fetch_signals: SMA50 failed for %s: %s", ticker, exc)

            if len(close) >= 200:
                try:
                    sma200_val = ta.trend.SMAIndicator(close=close, window=200).sma_indicator().iloc[-1]
                    sig["sma_200"] = None if (sma200_val != sma200_val) else round(float(sma200_val), 2)
                except Exception as exc:
                    logger.warning("fetch_signals: SMA200 failed for %s: %s", ticker, exc)

            return ticker, sig

        # Parallelize signal computation across tickers (CPU-bound pandas ops)
        to_compute = [t for t in valid if t in close_series]
        with ThreadPoolExecutor(max_workers=min(16, len(to_compute))) as pool:
            computed = list(pool.map(_compute_one, to_compute))

        # Write results to DB (single connection, serial writes)
        conn = sqlite3.connect(self.db_path)
        try:
            for ticker, sig in computed:
                results[ticker] = sig
                _cache_signals(conn, ticker, today_str, sig)
            conn.commit()
        finally:
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

        # Build queries — use names when available, else strip exchange suffixes from tickers.
        # Skip bond/FD tickers that start with digits (e.g. 1190VCCL26) — no news coverage.
        clean_names = [n for n in holding_names if n]
        if clean_names:
            holdings_query = " OR ".join(clean_names[:3])
        else:
            clean_tickers = [
                t.split(".")[0] for t in tickers
                if t and not t[0].isdigit()
            ]
            holdings_query = " OR ".join(clean_tickers[:3]) if clean_tickers else "stocks"

        tab_queries = {
            "holdings": holdings_query,
            "india": "India economy OR RBI OR Nifty OR NSE OR budget India",
            "germany": "Germany economy OR ECB OR DAX OR Bundesbank OR euro zone",
            "us": "Federal Reserve OR S&P500 OR Nasdaq OR US stocks OR earnings",
        }

        result = {}
        conn = sqlite3.connect(self.db_path)
        try:
            # Phase 1: check caches synchronously
            uncached_tabs = {}
            for tab, query in tab_queries.items():
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
                    else:
                        uncached_tabs[tab] = query
                except Exception as exc:
                    logger.warning("fetch_news: cache read failed for tab=%s: %s", tab, exc)
                    uncached_tabs[tab] = query

            # Phase 2: fetch uncached tabs from NewsAPI in parallel
            if uncached_tabs:
                articles_by_tab = {}

                def _fetch_tab(item):
                    tab, query = item
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
                    return tab, articles_list

                with ThreadPoolExecutor(max_workers=4) as pool:
                    futures = {pool.submit(_fetch_tab, item): item[0] for item in uncached_tabs.items()}
                    for future in as_completed(futures):
                        tab, articles_list = future.result()
                        articles_by_tab[tab] = articles_list

                # Phase 3: write results to cache synchronously
                for tab, articles_list in uncached_tabs.items():
                    result[tab] = articles_by_tab.get(tab, [])
                    try:
                        conn.execute(
                            "INSERT OR REPLACE INTO news_cache (query, date, articles_json) VALUES (?, ?, ?)",
                            (tab_queries[tab], today_str, json.dumps(articles_by_tab.get(tab, []))),
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
            # Phase 1: synchronously check caches for all tickers
            uncached = []
            for ticker in tickers:
                if not ticker:
                    continue
                try:
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
                    else:
                        uncached.append(ticker)
                except Exception as exc:
                    logger.warning("fetch_analyst: cache check failed for %s: %s", ticker, exc)
                    uncached.append(ticker)

            # Phase 2: parallelize Finnhub + yfinance calls for uncached tickers
            def _fetch_one_analyst(ticker: str) -> tuple:
                try:
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

                    # yfinance fallback — Finnhub free tier has no NSE coverage
                    if rating is None and target_mean is None:
                        try:
                            info = yf.Ticker(ticker).info
                            rec_key = info.get("recommendationKey", "")
                            if rec_key in ("strong_buy", "buy"):
                                rating = "BUY"
                            elif rec_key in ("sell", "strong_sell", "underperform"):
                                rating = "SELL"
                            elif rec_key in ("hold", "neutral"):
                                rating = "HOLD"
                            target_mean = info.get("targetMeanPrice")
                            num_analysts = info.get("numberOfAnalystOpinions")
                        except Exception as exc:
                            logger.warning("fetch_analyst: yfinance fallback failed for %s: %s", ticker, exc)

                    return ticker, {"rating": rating, "target_mean": target_mean, "num_analysts": num_analysts}
                except Exception as exc:
                    logger.warning("fetch_analyst: failed for %s: %s", ticker, exc)
                    return ticker, None

            if uncached:
                with ThreadPoolExecutor(max_workers=min(16, len(uncached))) as pool:
                    futures = {pool.submit(_fetch_one_analyst, t): t for t in uncached}
                    for future in as_completed(futures):
                        ticker, data = future.result()
                        if data is not None:
                            results[ticker] = data
                            # Cache to analyst_cache
                            try:
                                conn.execute(
                                    "INSERT OR REPLACE INTO analyst_cache (symbol, date, rating, target_mean, num_analysts) VALUES (?, ?, ?, ?, ?)",
                                    (ticker, today_str, data["rating"], data["target_mean"], data["num_analysts"]),
                                )
                            except Exception as exc:
                                logger.warning("fetch_analyst: cache write failed for %s: %s", ticker, exc)

            conn.commit()
        finally:
            conn.close()

        logger.info("fetch_analyst: fetched analyst data for %d/%d tickers", len(results), len(tickers))
        return results

    def fetch_benchmark(self, holdings: list) -> dict:
        """
        Compute portfolio and index returns for windows: 1D, 1W, 1M, 3M, YTD, 1Y.

        Parameters
        ----------
        holdings : list
            List of holding dicts. Each must have keys:
              ticker_yfinance (str), quantity (float), current_price (float|None),
              currency (str), asset_type (str), region (str).

        Returns
        -------
        dict
            Keys: windows, portfolio, indices, regional.
            Each window value is float (% return) or None when insufficient history.

        Security note: no SQL is executed; all yfinance calls are read-only.
        Fail-open: individual ticker/index failures return None for that cell.
        """
        WINDOWS = ["1D", "1W", "1M", "3M", "YTD", "1Y"]
        INDEX_TICKERS = ["^NSEI", "^GSPC", "^GDAXI"]

        # Empty shape — returned on failure or empty input
        empty_windows: dict = {w: None for w in WINDOWS}
        empty_shape: dict = {
            "windows": WINDOWS,
            "portfolio": dict(empty_windows),
            "indices": {
                "^NSEI":  dict(empty_windows),
                "^GSPC":  dict(empty_windows),
                "^GDAXI": dict(empty_windows),
            },
            "regional": {
                "india":          dict(empty_windows),
                "germany_us_etf": dict(empty_windows),
            },
        }

        # Filter to investable holdings (non-cash, non-zero quantity)
        investable = [
            h for h in holdings
            if h.get("ticker_yfinance")
            and h.get("asset_type") != "cash"
            and (h.get("quantity") or 0) > 0
        ]
        holding_tickers = [h["ticker_yfinance"] for h in investable]

        combined = list(dict.fromkeys(holding_tickers + INDEX_TICKERS))  # unique, preserving order
        if not combined:
            logger.warning("fetch_benchmark: no tickers to fetch")
            return empty_shape

        # One batch download covering 1Y of history (sufficient for all windows)
        try:
            raw = yf.download(
                tickers=" ".join(combined),
                period="1y",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception as exc:
            logger.warning("fetch_benchmark: yfinance.download raised: %s", exc)
            return empty_shape

        if raw is None or raw.empty:
            logger.warning("fetch_benchmark: yfinance returned empty DataFrame")
            return empty_shape

        # Helper: extract Close series for a single ticker from multi or single layout
        def _close_series(ticker: str):
            if ("Close", ticker) in raw.columns:
                series = raw.xs(ticker, axis=1, level=1)["Close"]
            elif len(combined) == 1 and "Close" in raw.columns:
                series = raw["Close"]
            else:
                return None
            series = series.dropna()
            return series if not series.empty else None

        # Helper: compute window return % for a Close series
        def _window_pct(series, window: str):
            start = _window_start(window)
            sliced = series[series.index.date >= start]
            if sliced.empty:
                return None
            start_close = float(sliced.iloc[0])
            end_close = float(sliced.iloc[-1])
            if start_close == 0:
                return None
            return (end_close - start_close) / start_close * 100

        # Per-ticker window returns
        ticker_window_pcts: dict[str, dict] = {}
        for ticker in combined:
            try:
                series = _close_series(ticker)
                if series is None:
                    logger.warning("fetch_benchmark: no Close data for %s", ticker)
                    ticker_window_pcts[ticker] = {w: None for w in WINDOWS}
                    continue
                ticker_window_pcts[ticker] = {
                    w: _window_pct(series, w) for w in WINDOWS
                }
            except Exception as exc:
                logger.warning("fetch_benchmark: failed for %s: %s", ticker, exc)
                ticker_window_pcts[ticker] = {w: None for w in WINDOWS}
                continue

        # Weighted aggregate for a list of holdings + per-window pcts
        def _weighted_avg(bucket_holdings: list, window: str):
            total_weight = 0.0
            weighted_sum = 0.0
            for h in bucket_holdings:
                t = h.get("ticker_yfinance")
                if not t:
                    continue
                pct = ticker_window_pcts.get(t, {}).get(window)
                if pct is None:
                    continue
                price = h.get("current_price") or 0.0
                qty = h.get("quantity") or 0.0
                weight = price * qty
                if weight <= 0:
                    continue
                weighted_sum += pct * weight
                total_weight += weight
            if total_weight == 0:
                return None
            return weighted_sum / total_weight

        # Build result
        result: dict = {
            "windows": WINDOWS,
            "portfolio": {},
            "indices": {
                "^NSEI":  {},
                "^GSPC":  {},
                "^GDAXI": {},
            },
            "regional": {
                "india":          {},
                "germany_us_etf": {},
            },
        }

        # Portfolio-level aggregate
        for w in WINDOWS:
            result["portfolio"][w] = _weighted_avg(investable, w)

        # Index returns
        for idx_ticker in INDEX_TICKERS:
            for w in WINDOWS:
                result["indices"][idx_ticker][w] = ticker_window_pcts.get(idx_ticker, {}).get(w)

        # Regional buckets
        india_holdings = [h for h in investable if h.get("region") == "india"]
        intl_holdings = [
            h for h in investable
            if h.get("region") in {"germany", "us", "etf"} or h.get("asset_type") == "etf"
        ]
        for w in WINDOWS:
            result["regional"]["india"][w] = _weighted_avg(india_holdings, w)
            result["regional"]["germany_us_etf"][w] = _weighted_avg(intl_holdings, w)

        logger.info(
            "fetch_benchmark: computed returns for %d holdings + %d indices",
            len(investable), len(INDEX_TICKERS),
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_symbol_frame(self, raw, symbol: str, symbols: list[str]):
        """Return a single-symbol OHLCV DataFrame from yfinance's single or multi layout."""
        if ("Close", symbol) in raw.columns:
            return raw.xs(symbol, axis=1, level=1)
        if len(symbols) == 1 and "Close" in raw.columns:
            return raw
        return None

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

    def _cache_live_price_to_db(self, conn: sqlite3.Connection, symbol: str, date_str: str, close: float) -> None:
        """Overlay the live last price onto *symbol*'s current-session row.

        Updates close/adj_close (and refreshes fetched_at) on an existing daily row
        to preserve its real OHLC/volume; inserts a flat-OHLC row when none exists
        yet (daily bar not published). Never disturbs the previous session's row.
        """
        try:
            cur = conn.execute(
                "UPDATE price_history SET close = ?, adj_close = ?, fetched_at = CURRENT_TIMESTAMP "
                "WHERE ticker = ? AND date = ?",
                (close, close, symbol, date_str),
            )
            if cur.rowcount == 0:
                conn.execute(
                    """
                    INSERT INTO price_history
                        (ticker, date, open, high, low, close, adj_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, date_str, close, close, close, close, close, 0),
                )
        except Exception as exc:
            logger.warning("Failed to cache live price for %s: %s", symbol, exc)

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
