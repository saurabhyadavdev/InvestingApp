"""
GET /api/recommendations — scan the curated stock universe for BUY signals.

Scoring per stock:
  RSI-14 < 35:          +3  (oversold — potential rebound)
  RSI-14 35–50:         +1  (healthy room to grow)
  MACD histogram > 0:   +2  (bullish momentum)
  Daily change > 0.5%:  +1  (positive price action today)
  Price > SMA-50:       +1  (in an uptrend)

Threshold: score >= 3 to qualify as a BUY pick.
Returns up to TOP_N picks per market, sorted by score descending.
"""
import logging
from datetime import datetime, timezone

import yfinance as yf
import pandas as pd
try:
    import ta.momentum as _tam
    import ta.trend as _tat
    _TA_AVAILABLE = True
except ImportError:
    _TA_AVAILABLE = False

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recommendations"])

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
        "label": "United States",
        "tickers": [
            "AAPL", "NVDA", "MSFT", "AMZN", "META",
            "TSLA", "GOOGL", "AVGO", "JPM", "LLY",
            "V", "UNH", "XOM", "MA", "HD",
            "NFLX", "AMD", "COST", "BAC", "PG",
        ],
    },
}

TOP_N = 5
MIN_SCORE = 3


def _short_name(ticker: str) -> str:
    """Strip exchange suffix for display."""
    return ticker.replace(".NS", "").replace(".DE", "")


def _score_stock(close: pd.Series, last_close: float, prev_close: float) -> tuple[int, list[str]]:
    """Return (score, signals_list) for a single stock."""
    score = 0
    signals = []

    if not _TA_AVAILABLE or len(close) < 15:
        return score, signals

    # RSI-14
    rsi = None
    try:
        rsi_series = _tam.RSIIndicator(close=close, window=14).rsi()
        rsi_val = rsi_series.iloc[-1]
        if rsi_val == rsi_val:  # not NaN
            rsi = round(float(rsi_val), 1)
    except Exception:
        pass

    if rsi is not None:
        if rsi < 35:
            score += 3
            signals.append(f"Oversold RSI {rsi}")
        elif rsi < 50:
            score += 1
            signals.append(f"RSI {rsi}")

    # MACD histogram
    if len(close) >= 26:
        try:
            macd_obj = _tat.MACD(close=close)
            hist = macd_obj.macd_diff().iloc[-1]
            if hist == hist and hist > 0:
                score += 2
                signals.append("Bullish MACD")
        except Exception:
            pass

    # Daily change
    if prev_close and prev_close > 0:
        daily_pct = (last_close - prev_close) / prev_close * 100
        if daily_pct > 0.5:
            score += 1
            signals.append(f"+{daily_pct:.1f}% today")

    # Price above SMA-50
    if len(close) >= 50:
        try:
            sma50 = _tat.SMAIndicator(close=close, window=50).sma_indicator().iloc[-1]
            if sma50 == sma50 and last_close > float(sma50):
                score += 1
                signals.append("Above SMA-50")
        except Exception:
            pass

    return score, signals


def _scan_market(tickers: list[str]) -> list[dict]:
    """Fetch 6mo OHLCV, score each ticker, return top BUY picks."""
    try:
        raw = yf.download(
            tickers,
            period="6mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        logger.warning("recommendations: yfinance download failed: %s", exc)
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

            df = df.dropna(subset=["Close"])
            if len(df) < 2:
                continue

            close = df["Close"]
            last_close = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            score, signals = _score_stock(close, last_close, prev_close)
            if score < MIN_SCORE:
                continue

            daily_pct = round((last_close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
            rsi_val = None
            try:
                if _TA_AVAILABLE and len(close) >= 15:
                    r = _tam.RSIIndicator(close=close, window=14).rsi().iloc[-1]
                    if r == r:
                        rsi_val = round(float(r), 1)
            except Exception:
                pass

            results.append({
                "ticker": ticker,
                "name": _short_name(ticker),
                "close": round(last_close, 2),
                "change_pct": daily_pct,
                "rsi_14": rsi_val,
                "score": score,
                "signals": signals,
            })

        except Exception as exc:
            logger.debug("recommendations: skipping %s: %s", ticker, exc)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:TOP_N]


@router.get("/recommendations")
async def get_recommendations():
    """
    Scan the curated stock universe for BUY opportunities.

    Scoring: RSI oversold (+3), healthy RSI (+1), bullish MACD (+2),
             positive daily move (+1), above SMA-50 (+1). Min score: 3.

    Response
    --------
    {
      "markets": {
        "india":   {"label": "India (NSE)",   "picks": [...]},
        "germany": {"label": "Germany (XETRA)", "picks": [...]},
        "us":      {"label": "United States",  "picks": [...]}
      },
      "fetched_at": "<UTC ISO 8601>"
    }

    Each pick: {ticker, name, close, change_pct, rsi_14, score, signals}
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    markets_out = {}
    for key, meta in _MARKETS.items():
        picks = _scan_market(meta["tickers"])
        markets_out[key] = {"label": meta["label"], "picks": picks}

    return {"markets": markets_out, "fetched_at": fetched_at}
