"""
GET /api/trending — return top 5 most-traded stocks per market (India, Germany, US).

Uses yfinance to fetch 1-day price/volume data for a curated universe of
liquid tickers per exchange, then ranks by volume descending.
"""
import logging
from datetime import datetime, timezone

import yfinance as yf
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["trending"])

# Curated universe: ~20 liquid names per market — ranked by volume on fetch
_MARKETS = {
    "india": {
        "label": "India (NSE)",
        "tickers": [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
            "SBIN.NS", "BAJFINANCE.NS", "AXISBANK.NS", "WIPRO.NS", "LT.NS",
            "KOTAKBANK.NS", "TATAMOTORS.NS", "ONGC.NS", "MARUTI.NS", "NTPC.NS",
            "ADANIENT.NS", "BHARTIARTL.NS", "SUNPHARMA.NS", "POWERGRID.NS", "M&M.NS",
        ],
    },
    "germany": {
        "label": "Germany (XETRA)",
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "BMW.DE",
            "MBG.DE", "BAYN.DE", "VOW3.DE", "MRK.DE", "BAS.DE",
            "DBK.DE", "ADS.DE", "HEN3.DE", "IFX.DE", "ENR.DE",
            "1COV.DE", "RWE.DE", "MTX.DE", "FRE.DE", "HEI.DE",
        ],
    },
    "us": {
        "label": "United States (NYSE/NASDAQ)",
        "tickers": [
            "AAPL", "NVDA", "MSFT", "AMZN", "META",
            "TSLA", "GOOGL", "AVGO", "JPM", "LLY",
            "V", "UNH", "XOM", "MA", "HD",
            "NFLX", "AMD", "COST", "BAC", "PG",
        ],
    },
}

_TOP_N = 5


def _fetch_market(tickers: list[str]) -> list[dict]:
    """Fetch 2-day OHLCV for tickers, compute change_pct, return sorted by volume."""
    try:
        raw = yf.download(
            tickers,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        logger.warning("yfinance download failed: %s", exc)
        return []

    results = []
    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = raw
            else:
                df = raw[ticker] if ticker in raw.columns.get_level_values(0) else None

            if df is None or df.empty:
                continue

            df = df.dropna(subset=["Close", "Volume"])
            if len(df) < 1:
                continue

            last = df.iloc[-1]
            volume = float(last["Volume"]) if last["Volume"] > 0 else 0
            close = float(last["Close"])
            change_pct = 0.0
            if len(df) >= 2:
                prev_close = float(df.iloc[-2]["Close"])
                if prev_close > 0:
                    change_pct = round((close - prev_close) / prev_close * 100, 2)

            results.append({
                "ticker": ticker,
                "close": round(close, 2),
                "change_pct": change_pct,
                "volume": int(volume),
            })
        except Exception as exc:
            logger.debug("Skipping %s: %s", ticker, exc)

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:_TOP_N]


@router.get("/trending")
async def get_trending():
    """
    Return the 5 most-traded stocks per market by volume (today or last close).

    Response
    --------
    {
      "markets": {
        "india":   {"label": "India (NSE)",   "stocks": [...]},
        "germany": {"label": "Germany (XETRA)", "stocks": [...]},
        "us":      {"label": "United States",  "stocks": [...]}
      },
      "fetched_at": "<UTC ISO 8601>"
    }

    Each stock: {"ticker", "close", "change_pct", "volume"}
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    markets_out = {}
    for key, meta in _MARKETS.items():
        stocks = _fetch_market(meta["tickers"])
        markets_out[key] = {"label": meta["label"], "stocks": stocks}

    return {"markets": markets_out, "fetched_at": fetched_at}
