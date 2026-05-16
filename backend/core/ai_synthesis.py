"""
AI synthesis module for InvestIQ.

Derives per-holding BUY/HOLD/SELL recommendations using a two-stage approach:
  1. Rule-based fallback (rec_from_signals) using RSI, MACD histogram, and analyst consensus.
  2. Claude Haiku 4.5 confirmation/override with 2-3 sentence plain-English narrative.

Security notes (T-02-12, T-02-13, T-02-18):
  - User data passed to Claude as assistant context only, never in the system prompt user field.
  - ANTHROPIC_API_KEY never logged or included in returned data.
  - JSON parse fallback (regex) prevents crashes on malformed Claude output.
  - Cash context included in Claude prompt when idle cash > 1000 in any broker (FX-04).
"""
import json
import logging
import re

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)


def rec_from_signals(signals: dict, analyst: dict) -> str:
    """
    Rule-based recommendation derivation from technical signals and analyst consensus.

    Parameters
    ----------
    signals : dict
        Technical signals dict with keys: rsi_14, macd_histogram (float or None).
    analyst : dict
        Analyst data dict with key: rating ("BUY" | "HOLD" | "SELL" | None).

    Returns
    -------
    str
        "BUY", "HOLD", or "SELL".
    """
    buy_votes = 0
    sell_votes = 0

    rsi_14 = signals.get("rsi_14")
    macd_histogram = signals.get("macd_histogram")

    # RSI signals
    if rsi_14 is not None and rsi_14 < 35:
        buy_votes += 2  # oversold
    if rsi_14 is not None and rsi_14 > 65:
        sell_votes += 1  # overbought

    # MACD histogram signals
    if macd_histogram is not None and macd_histogram > 0:
        buy_votes += 1  # bullish momentum
    if macd_histogram is not None and macd_histogram < 0:
        sell_votes += 1  # bearish momentum

    # Analyst consensus
    if analyst.get("rating") == "BUY":
        buy_votes += 2
    if analyst.get("rating") == "SELL":
        sell_votes += 2

    if buy_votes > sell_votes and buy_votes >= 2:
        return "BUY"
    elif sell_votes > buy_votes and sell_votes >= 2:
        return "SELL"
    return "HOLD"


def synthesise_holding(
    client: anthropic.Anthropic,
    ticker: str,
    pl_pct: float,
    signals: dict,
    analyst: dict,
    cash_context,
) -> tuple:
    """
    Call Claude Haiku 4.5 to generate a BUY/HOLD/SELL recommendation and 2-3 sentence narrative.

    Parameters
    ----------
    client : anthropic.Anthropic
        Initialized Anthropic client.
    ticker : str
        Ticker symbol (used in context string only).
    pl_pct : float
        Current P&L percentage.
    signals : dict
        Technical signals dict.
    analyst : dict
        Analyst data dict.
    cash_context : str | None
        Optional cash deployment context string.

    Returns
    -------
    tuple[str, str]
        (rec: "BUY" | "HOLD" | "SELL", narrative: str)

    Behaviour
    ---------
    - Anti-hallucination prompt: "Based ONLY on the data below" (D-08 mitigation, T-02-12).
    - JSON parse failure: regex fallback extracts {…} block; ultimate fallback = rule-based rec.
    - Any exception: logs warning, returns (rec_from_signals(signals, analyst), generic narrative).
    """
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
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Primary parse
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Regex fallback: extract first {...} block (T-02-18 mitigation)
            m = re.search(r"\{.*?\}", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
            else:
                raise ValueError("no JSON found in Claude response")

        return parsed.get("rec", "HOLD"), parsed.get(
            "narrative", "Signal data available but AI synthesis unavailable."
        )

    except Exception as exc:
        logger.warning("synthesise_holding failed for %s: %s", ticker, exc)
        return (
            rec_from_signals(signals, analyst),
            "Signal data available but AI synthesis unavailable.",
        )


def synthesise_holdings(
    portfolio_data: dict,
    signals_data: dict,
    analyst_data: dict,
    cash_by_broker: dict,
) -> list:
    """
    Enrich each holding in portfolio_data with rec, analyst fields, and AI narrative.

    Parameters
    ----------
    portfolio_data : dict
        Portfolio dict with "holdings" list.
    signals_data : dict
        {ticker: {rsi_14, macd_histogram, ...}} from fetch_signals.
    analyst_data : dict
        {ticker: {rating, target_mean, num_analysts}} from fetch_analyst.
    cash_by_broker : dict
        {broker_name: cash_balance} — used for FX-04 cash deployment context.

    Returns
    -------
    list
        Enriched holdings list. Each holding gains:
          rec, analyst_rating, analyst_target, analyst_num, ai_narrative.

    Behaviour
    ---------
    - If ANTHROPIC_API_KEY is empty: uses rule-based rec only; sets generic ai_narrative.
    - Cash deployment context injected when any broker cash balance > 1000 (FX-04).
    - ANTHROPIC_API_KEY never appears in returned data (T-02-13).
    """
    holdings = portfolio_data.get("holdings", [])

    if not settings.ANTHROPIC_API_KEY:
        for h in holdings:
            signals = signals_data.get(h["ticker"], {})
            analyst = analyst_data.get(h["ticker"], {})
            h["analyst_rating"] = analyst.get("rating")
            h["analyst_target"] = analyst.get("target_mean")
            h["analyst_num"] = analyst.get("num_analysts")
            h["rec"] = rec_from_signals(signals, analyst)
            h["ai_narrative"] = "AI synthesis unavailable — set ANTHROPIC_API_KEY in .env"
        return holdings

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build cash deployment context string (FX-04)
    cash_context = None
    if any(v > 1000 for v in (cash_by_broker or {}).values()):
        cash_list = ", ".join(
            f"{b}: {a}" for b, a in cash_by_broker.items() if a > 1000
        )
        cash_context = (
            f"Idle cash available: {cash_list}. "
            "Consider deployment if market conditions are favourable."
        )

    for h in holdings:
        signals = signals_data.get(h["ticker"], {})
        analyst = analyst_data.get(h["ticker"], {})

        h["analyst_rating"] = analyst.get("rating")
        h["analyst_target"] = analyst.get("target_mean")
        h["analyst_num"] = analyst.get("num_analysts")

        rec, narrative = synthesise_holding(
            client,
            h["ticker"],
            h.get("pl_pct", 0),
            signals,
            analyst,
            cash_context,
        )
        h["rec"] = rec
        h["ai_narrative"] = narrative

    return holdings
