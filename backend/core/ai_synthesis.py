"""
AI synthesis module for InvestIQ — uses Groq (llama-3.3-70b, free tier).

Derives per-holding BUY/HOLD/SELL recommendations using a two-stage approach:
  1. Rule-based fallback (rec_from_signals) using RSI, MACD histogram, and analyst consensus.
  2. Groq Llama confirmation/override with 2-3 sentence plain-English narrative.
"""
import json
import logging
import re

from groq import Groq

from backend.config import settings

logger = logging.getLogger(__name__)


def rec_from_signals(signals: dict, analyst: dict) -> str:
    buy_votes = 0
    sell_votes = 0

    rsi_14 = signals.get("rsi_14")
    macd_histogram = signals.get("macd_histogram")

    if rsi_14 is not None and rsi_14 < 35:
        buy_votes += 2
    if rsi_14 is not None and rsi_14 > 65:
        sell_votes += 1
    if macd_histogram is not None and macd_histogram > 0:
        buy_votes += 1
    if macd_histogram is not None and macd_histogram < 0:
        sell_votes += 1
    if analyst.get("rating") == "BUY":
        buy_votes += 2
    if analyst.get("rating") == "SELL":
        sell_votes += 2

    if buy_votes > sell_votes and buy_votes >= 2:
        return "BUY"
    elif sell_votes > buy_votes and sell_votes >= 2:
        return "SELL"
    return "HOLD"


def synthesise_holding(client, ticker: str, pl_pct: float, signals: dict, analyst: dict, cash_context) -> tuple:
    context = (
        f"Ticker: {ticker}\n"
        f"P&L: {pl_pct:.1f}%\n"
        f"RSI-14: {signals.get('rsi_14', 'N/A')}\n"
        f"MACD: {signals.get('macd', 'N/A')}\n"
        f"MACD Histogram: {signals.get('macd_histogram', 'N/A')}\n"
        f"SMA50: {signals.get('sma_50', 'N/A')}\n"
        f"SMA200: {signals.get('sma_200', 'N/A')}\n"
        f"Analyst Rating: {analyst.get('rating', 'N/A')}\n"
        f"Analyst Target: {analyst.get('target_mean', 'N/A')}\n"
        f"Analyst Count: {analyst.get('num_analysts', 'N/A')}"
    )
    if cash_context:
        context += f"\n{cash_context}"

    prompt = (
        'You are a personal investing analyst. Based ONLY on the data below, output a JSON object '
        'with two keys: {"rec": "BUY"|"HOLD"|"SELL", "narrative": "<2-3 sentence plain-English explanation>"}. '
        'Do not invent facts not in the data. If data is missing, say so briefly.\n\nData:\n' + context
    )

    try:
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        raw = message.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
            else:
                raise ValueError("no JSON found in response")

        return parsed.get("rec", "HOLD"), parsed.get(
            "narrative", "Signal data available but AI synthesis unavailable."
        )

    except Exception as exc:
        logger.warning("synthesise_holding failed for %s: %s", ticker, exc)
        return (
            rec_from_signals(signals, analyst),
            "Signal data available but AI synthesis unavailable.",
        )


def synthesise_holding_ondemand(client, ticker: str, signals: dict, analyst: dict, recent_news: list) -> dict:
    """Return structured AI analysis with three keys: today_move, recommendation, outlook.

    Never raises — returns all-None dict on any failure.
    """
    try:
        headlines = "\n".join(
            f"- {h.get('title', h) if isinstance(h, dict) else h}"
            for h in recent_news[:3]
        ) or "No recent news available."

        context = (
            f"Ticker: {ticker}\n"
            f"RSI-14: {signals.get('rsi_14', 'N/A')}\n"
            f"MACD: {signals.get('macd', 'N/A')}\n"
            f"MACD Histogram: {signals.get('macd_histogram', 'N/A')}\n"
            f"SMA50: {signals.get('sma_50', 'N/A')}\n"
            f"SMA200: {signals.get('sma_200', 'N/A')}\n"
            f"Analyst Rating: {analyst.get('rating', 'N/A')}\n"
            f"Analyst Target: {analyst.get('target_mean', 'N/A')}\n"
            f"Recent News Headlines:\n{headlines}"
        )

        prompt = (
            "You are a personal investing analyst. Based ONLY on the data below, output a JSON object "
            "with exactly three keys: today_move, recommendation, outlook. Each value is 1-2 sentences "
            "plain English. Do not invent facts not in the data.\n\nData:\n" + context
        )

        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
        )
        raw = message.choices[0].message.content.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
            else:
                raise ValueError("no JSON found in response")

        return {
            "today_move": parsed.get("today_move"),
            "recommendation": parsed.get("recommendation"),
            "outlook": parsed.get("outlook"),
        }

    except Exception as exc:
        logger.warning("synthesise_holding_ondemand failed for %s: %s", ticker, exc)
        return {"today_move": None, "recommendation": None, "outlook": None}


def synthesise_holdings(portfolio_data: dict, signals_data: dict, analyst_data: dict, cash_by_broker: dict) -> list:
    holdings = portfolio_data.get("holdings", [])

    # signals_data and analyst_data are keyed by ticker_yfinance (e.g. "AAVAS.NS").
    # Use ticker_yfinance from the holding dict for lookups; fall back to empty dict
    # for holdings with no yfinance mapping (e.g. Trade Republic positions).

    if not settings.GROQ_API_KEY:
        for h in holdings:
            yf_ticker = h.get("ticker_yfinance")
            signals = signals_data.get(yf_ticker, {}) if yf_ticker else {}
            analyst = analyst_data.get(yf_ticker, {}) if yf_ticker else {}
            h["analyst_rating"] = analyst.get("rating")
            h["analyst_target"] = analyst.get("target_mean")
            h["analyst_num"] = analyst.get("num_analysts")
            h["rec"] = rec_from_signals(signals, analyst)
            h["ai_narrative"] = "AI synthesis unavailable — set GROQ_API_KEY in .env"
        return holdings

    client = Groq(api_key=settings.GROQ_API_KEY)

    cash_context = None
    if any(v > 1000 for v in (cash_by_broker or {}).values()):
        cash_list = ", ".join(f"{b}: {a}" for b, a in cash_by_broker.items() if a > 1000)
        cash_context = (
            f"Idle cash available: {cash_list}. "
            "Consider deployment if market conditions are favourable."
        )

    for h in holdings:
        yf_ticker = h.get("ticker_yfinance")
        signals = signals_data.get(yf_ticker, {}) if yf_ticker else {}
        analyst = analyst_data.get(yf_ticker, {}) if yf_ticker else {}

        h["analyst_rating"] = analyst.get("rating")
        h["analyst_target"] = analyst.get("target_mean")
        h["analyst_num"] = analyst.get("num_analysts")

        # Only call AI when we have real signal data — avoids burning rate limit on tickers
        # with no OHLCV history (returns null signals from fetch_signals)
        has_signals = signals.get("rsi_14") is not None
        if has_signals:
            rec, narrative = synthesise_holding(client, h["ticker"], h.get("pl_pct", 0), signals, analyst, cash_context)
        else:
            rec = rec_from_signals(signals, analyst)
            narrative = "Insufficient price history for AI analysis."
        h["rec"] = rec
        h["ai_narrative"] = narrative

    return holdings
