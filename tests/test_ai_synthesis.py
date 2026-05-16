"""
Tests for backend/core/ai_synthesis.py — Plan 02-04 TDD.
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# rec_from_signals tests
# ---------------------------------------------------------------------------

def test_rec_from_signals_buy():
    """rec_from_signals returns BUY when rsi_14=30, macd_histogram=0.5, analyst rating=BUY."""
    from backend.core.ai_synthesis import rec_from_signals
    signals = {"rsi_14": 30, "macd_histogram": 0.5}
    analyst = {"rating": "BUY"}
    result = rec_from_signals(signals, analyst)
    assert result == "BUY"


def test_rec_from_signals_hold_neutral():
    """rec_from_signals returns HOLD when signals and analyst are neutral/None."""
    from backend.core.ai_synthesis import rec_from_signals
    signals = {}
    analyst = {}
    result = rec_from_signals(signals, analyst)
    assert result == "HOLD"


def test_rec_from_signals_hold_none_values():
    """rec_from_signals returns HOLD when all signal values are None and analyst has no rating."""
    from backend.core.ai_synthesis import rec_from_signals
    signals = {"rsi_14": None, "macd_histogram": None}
    analyst = {"rating": None}
    result = rec_from_signals(signals, analyst)
    assert result == "HOLD"


def test_rec_from_signals_sell():
    """rec_from_signals returns SELL when rsi > 65, macd_histogram < 0, analyst = SELL."""
    from backend.core.ai_synthesis import rec_from_signals
    signals = {"rsi_14": 75, "macd_histogram": -0.5}
    analyst = {"rating": "SELL"}
    result = rec_from_signals(signals, analyst)
    assert result == "SELL"


def test_rec_from_signals_analyst_buy_only():
    """rec_from_signals returns BUY when only analyst rating is BUY (buy_votes = 2 >= 2)."""
    from backend.core.ai_synthesis import rec_from_signals
    signals = {}
    analyst = {"rating": "BUY"}
    result = rec_from_signals(signals, analyst)
    assert result == "BUY"


# ---------------------------------------------------------------------------
# fetch_analyst empty key test
# ---------------------------------------------------------------------------

def test_fetch_analyst_returns_empty_when_no_key(tmp_path):
    """fetch_analyst returns {} when FINNHUB_KEY is empty."""
    from backend.core.data_fetcher import DataFetcher

    # Use a temp DB with schema
    db_file = str(tmp_path / "test.db")
    from backend.database import create_schema
    create_schema(db_file)

    fetcher = DataFetcher(db_file)
    with patch("backend.core.data_fetcher.settings") as mock_settings:
        mock_settings.FINNHUB_KEY = ""
        result = fetcher.fetch_analyst(["RELIANCE.NS", "AAPL"])

    assert result == {}


# ---------------------------------------------------------------------------
# synthesise_holdings without API key test
# ---------------------------------------------------------------------------

def test_synthesise_holdings_no_api_key():
    """synthesise_holdings sets ai_narrative to unavailable message when ANTHROPIC_API_KEY is empty."""
    from backend.core.ai_synthesis import synthesise_holdings

    portfolio_data = {
        "holdings": [
            {"ticker": "RELIANCE.NS", "pl_pct": 5.0},
        ]
    }
    signals_data = {"RELIANCE.NS": {"rsi_14": 50, "macd_histogram": 0.1}}
    analyst_data = {"RELIANCE.NS": {"rating": "BUY", "target_mean": 3000.0, "num_analysts": 5}}
    cash_by_broker = {}

    with patch("backend.core.ai_synthesis.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        result = synthesise_holdings(portfolio_data, signals_data, analyst_data, cash_by_broker)

    assert len(result) == 1
    h = result[0]
    assert "rec" in h
    assert "ai_narrative" in h
    assert "unavailable" in h["ai_narrative"].lower()
    assert h["analyst_rating"] == "BUY"
    assert h["analyst_target"] == 3000.0
    assert h["analyst_num"] == 5
