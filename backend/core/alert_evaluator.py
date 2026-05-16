"""
alert_evaluator: evaluate configured alert rules against live portfolio data.

Reads settings from the SQLite settings table (alert_* keys).
Returns a list of fired alert dicts: {ticker, type, message}.

Security note:
  - All SQL uses parameterized ? placeholders — no f-string SQL.
  - evaluate_alerts never raises; per-ticker exceptions are caught and logged.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def evaluate_alerts(
    holdings: list,
    signals: dict,
    analyst_prev: dict,
    analyst_curr: dict,
    settings: dict,
) -> list[dict]:
    """
    Evaluate all configured alert rules against the current portfolio state.

    Parameters
    ----------
    holdings : list of dicts
        Each dict has keys: ticker (display), ticker_yfinance, current_price,
        daily_pct, rsi_14 (may be None).
    signals : dict
        Keyed by ticker_yfinance; values are dicts with rsi_14, macd, etc.
        (Signals already merged into holdings in briefing step 4, but signals
        dict is passed as well for completeness.)
    analyst_prev : dict
        Keyed by symbol (ticker_yfinance); values: {"rating": str, "target": float}.
        Represents yesterday's analyst data. Empty dict if no history available.
    analyst_curr : dict
        Keyed by symbol (ticker_yfinance); values: {"rating": str, "target": float}.
        Represents today's analyst data.
    settings : dict
        Key-value pairs from the settings table filtered to alert_* keys.

    Returns
    -------
    list of dicts, each with keys: ticker, type, message.
    Empty list when no alerts fire or no settings are enabled.
    """
    fired: list[dict] = []

    for holding in holdings:
        ticker_yf = holding.get("ticker_yfinance") or holding.get("ticker") or ""
        ticker_display = holding.get("ticker") or ticker_yf

        try:
            _evaluate_price_alert(holding, ticker_yf, ticker_display, settings, fired)
        except Exception as exc:
            logger.warning("evaluate_alerts: price alert failed for %s: %s", ticker_display, exc)

        try:
            _evaluate_daily_move_alert(holding, ticker_yf, ticker_display, settings, fired)
        except Exception as exc:
            logger.warning("evaluate_alerts: daily_move alert failed for %s: %s", ticker_display, exc)

        try:
            _evaluate_rsi_alert(holding, ticker_yf, ticker_display, settings, fired)
        except Exception as exc:
            logger.warning("evaluate_alerts: rsi alert failed for %s: %s", ticker_display, exc)

        try:
            _evaluate_analyst_alert(ticker_yf, ticker_display, analyst_prev, analyst_curr, settings, fired)
        except Exception as exc:
            logger.warning("evaluate_alerts: analyst alert failed for %s: %s", ticker_display, exc)

    return fired


# ---------------------------------------------------------------------------
# Per-alert-type helpers
# ---------------------------------------------------------------------------

def _evaluate_price_alert(
    holding: dict,
    ticker_yf: str,
    ticker_display: str,
    settings: dict,
    fired: list,
) -> None:
    """Fire a 'price' alert when enabled and current price >= target."""
    enabled_key = f"alert_price_{ticker_yf}_enabled"
    price_key = f"alert_price_{ticker_yf}"

    if settings.get(enabled_key) != "true":
        return

    target_str = settings.get(price_key, "")
    if not target_str:
        return

    try:
        target = float(target_str)
    except (ValueError, TypeError):
        return

    if target <= 0:
        return

    current_price = holding.get("current_price")
    if current_price is None:
        return

    try:
        current_price = float(current_price)
    except (ValueError, TypeError):
        return

    if current_price >= target:
        fired.append({
            "ticker": ticker_yf,
            "type": "price",
            "message": (
                f"{ticker_display} price target crossed: "
                f"target {target:.2f}, current {current_price:.2f}"
            ),
        })


def _evaluate_daily_move_alert(
    holding: dict,
    ticker_yf: str,
    ticker_display: str,
    settings: dict,
    fired: list,
) -> None:
    """Fire a 'daily_move' alert when enabled and |daily_pct| >= threshold."""
    if settings.get("alert_daily_move_enabled") != "true":
        return

    threshold_str = settings.get("alert_daily_move_pct", "")
    if not threshold_str:
        return

    try:
        threshold = float(threshold_str)
    except (ValueError, TypeError):
        return

    daily_pct = holding.get("daily_pct")
    if daily_pct is None:
        return

    try:
        daily_pct = float(daily_pct)
    except (ValueError, TypeError):
        return

    if abs(daily_pct) >= threshold:
        sign = "+" if daily_pct >= 0 else ""
        fired.append({
            "ticker": ticker_yf,
            "type": "daily_move",
            "message": f"{ticker_display} moved {sign}{daily_pct:.1f}% today",
        })


def _evaluate_rsi_alert(
    holding: dict,
    ticker_yf: str,
    ticker_display: str,
    settings: dict,
    fired: list,
) -> None:
    """Fire an 'rsi' alert when enabled and RSI is overbought (>=70) or oversold (<=30)."""
    if settings.get("alert_rsi_enabled") != "true":
        return

    rsi = holding.get("rsi_14")
    if rsi is None:
        return

    try:
        rsi = float(rsi)
    except (ValueError, TypeError):
        return

    if rsi >= 70:
        fired.append({
            "ticker": ticker_yf,
            "type": "rsi",
            "message": f"{ticker_display} RSI crossed 70 (overbought — RSI: {rsi:.0f})",
        })
    elif rsi <= 30:
        fired.append({
            "ticker": ticker_yf,
            "type": "rsi",
            "message": f"{ticker_display} RSI crossed 30 (oversold — RSI: {rsi:.0f})",
        })


def _evaluate_analyst_alert(
    ticker_yf: str,
    ticker_display: str,
    analyst_prev: dict,
    analyst_curr: dict,
    settings: dict,
    fired: list,
) -> None:
    """
    Fire an 'analyst' alert when enabled and the analyst rating changed since yesterday.

    Graceful fallback per RESEARCH.md Pitfall 4: if yesterday's row is missing,
    do NOT fire (we cannot determine that a change occurred).
    """
    if settings.get("alert_analyst_enabled") != "true":
        return

    prev_entry = analyst_prev.get(ticker_yf, {})
    curr_entry = analyst_curr.get(ticker_yf, {})

    prev_rating = prev_entry.get("rating") if prev_entry else None
    curr_rating = curr_entry.get("rating") if curr_entry else None

    # Both must be present and truthy to determine that a change occurred
    if not prev_rating or not curr_rating:
        return

    if prev_rating != curr_rating:
        fired.append({
            "ticker": ticker_yf,
            "type": "analyst",
            "message": (
                f"{ticker_display} analyst consensus changed to {curr_rating}"
            ),
        })
