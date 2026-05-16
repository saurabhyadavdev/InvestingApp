"""
Tests for backend/core/alert_evaluator.py

Each of the four alert types has:
  - one positive case (alert fires)
  - one negative case (alert does not fire)

Plus the analyst-no-yesterday-row fallback test.
"""
import pytest
from backend.core.alert_evaluator import evaluate_alerts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_holding(
    ticker="HDFCBANK.NS",
    ticker_yfinance="HDFCBANK.NS",
    current_price=1600.0,
    daily_pct=3.0,
    rsi_14=72.0,
):
    return {
        "ticker": ticker,
        "ticker_yfinance": ticker_yfinance,
        "current_price": current_price,
        "daily_pct": daily_pct,
        "rsi_14": rsi_14,
    }


# ---------------------------------------------------------------------------
# Price Target Alerts
# ---------------------------------------------------------------------------

class TestPriceAlert:
    def test_fires_when_price_at_or_above_target(self):
        holding = _make_holding(ticker_yfinance="HDFCBANK.NS", current_price=1600.0)
        settings = {
            "alert_price_HDFCBANK.NS": "1500.0",
            "alert_price_HDFCBANK.NS_enabled": "true",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["type"] == "price"
        assert alert["ticker"] == "HDFCBANK.NS"
        assert "1500" in alert["message"]
        assert "1600" in alert["message"]

    def test_does_not_fire_when_price_below_target(self):
        holding = _make_holding(ticker_yfinance="HDFCBANK.NS", current_price=1400.0)
        settings = {
            "alert_price_HDFCBANK.NS": "1500.0",
            "alert_price_HDFCBANK.NS_enabled": "true",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_disabled(self):
        holding = _make_holding(ticker_yfinance="HDFCBANK.NS", current_price=1600.0)
        settings = {
            "alert_price_HDFCBANK.NS": "1500.0",
            "alert_price_HDFCBANK.NS_enabled": "false",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_no_current_price(self):
        holding = _make_holding(ticker_yfinance="HDFCBANK.NS", current_price=None)
        settings = {
            "alert_price_HDFCBANK.NS": "1500.0",
            "alert_price_HDFCBANK.NS_enabled": "true",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []


# ---------------------------------------------------------------------------
# Daily Move Alerts
# ---------------------------------------------------------------------------

class TestDailyMoveAlert:
    def test_fires_when_move_exceeds_threshold(self):
        holding = _make_holding(daily_pct=6.0)
        settings = {
            "alert_daily_move_enabled": "true",
            "alert_daily_move_pct": "5.0",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["type"] == "daily_move"
        assert "6.0" in alert["message"]

    def test_fires_on_negative_move_exceeding_threshold(self):
        holding = _make_holding(daily_pct=-7.5)
        settings = {
            "alert_daily_move_enabled": "true",
            "alert_daily_move_pct": "5.0",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "daily_move"
        assert "-7.5" in alerts[0]["message"]

    def test_does_not_fire_when_move_below_threshold(self):
        holding = _make_holding(daily_pct=2.0)
        settings = {
            "alert_daily_move_enabled": "true",
            "alert_daily_move_pct": "5.0",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_disabled(self):
        holding = _make_holding(daily_pct=10.0)
        settings = {
            "alert_daily_move_enabled": "false",
            "alert_daily_move_pct": "5.0",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_daily_pct_is_none(self):
        holding = _make_holding(daily_pct=None)
        settings = {
            "alert_daily_move_enabled": "true",
            "alert_daily_move_pct": "5.0",
        }
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []


# ---------------------------------------------------------------------------
# RSI Alerts
# ---------------------------------------------------------------------------

class TestRSIAlert:
    def test_fires_on_overbought(self):
        holding = _make_holding(rsi_14=72.0)
        settings = {"alert_rsi_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["type"] == "rsi"
        assert "overbought" in alert["message"]
        assert "72" in alert["message"]

    def test_fires_on_oversold(self):
        holding = _make_holding(rsi_14=28.0)
        settings = {"alert_rsi_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["type"] == "rsi"
        assert "oversold" in alert["message"]
        assert "28" in alert["message"]

    def test_does_not_fire_in_neutral_range(self):
        holding = _make_holding(rsi_14=55.0)
        settings = {"alert_rsi_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_disabled(self):
        holding = _make_holding(rsi_14=80.0)
        settings = {"alert_rsi_enabled": "false"}
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []

    def test_does_not_fire_when_rsi_is_none(self):
        holding = _make_holding(rsi_14=None)
        settings = {"alert_rsi_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, {}, {}, settings)
        assert alerts == []


# ---------------------------------------------------------------------------
# Analyst Rating Change Alerts
# ---------------------------------------------------------------------------

class TestAnalystAlert:
    def test_fires_when_rating_changed(self):
        holding = _make_holding(ticker_yfinance="INFY.NS")
        analyst_prev = {"INFY.NS": {"rating": "HOLD", "target": 1800.0}}
        analyst_curr = {"INFY.NS": {"rating": "BUY", "target": 2000.0}}
        settings = {"alert_analyst_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, analyst_prev, analyst_curr, settings)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["type"] == "analyst"
        assert "BUY" in alert["message"]

    def test_does_not_fire_when_rating_unchanged(self):
        holding = _make_holding(ticker_yfinance="INFY.NS")
        analyst_prev = {"INFY.NS": {"rating": "BUY", "target": 1800.0}}
        analyst_curr = {"INFY.NS": {"rating": "BUY", "target": 2000.0}}
        settings = {"alert_analyst_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, analyst_prev, analyst_curr, settings)
        assert alerts == []

    def test_does_not_fire_when_disabled(self):
        holding = _make_holding(ticker_yfinance="INFY.NS")
        analyst_prev = {"INFY.NS": {"rating": "HOLD", "target": 1800.0}}
        analyst_curr = {"INFY.NS": {"rating": "BUY", "target": 2000.0}}
        settings = {"alert_analyst_enabled": "false"}
        alerts = evaluate_alerts([holding], {}, analyst_prev, analyst_curr, settings)
        assert alerts == []

    def test_does_not_fire_when_no_yesterday_row(self):
        """
        RESEARCH.md Pitfall 4: if yesterday's row is missing, do NOT fire.
        We cannot know that a change occurred.
        """
        holding = _make_holding(ticker_yfinance="INFY.NS")
        analyst_prev = {}  # no history
        analyst_curr = {"INFY.NS": {"rating": "BUY", "target": 2000.0}}
        settings = {"alert_analyst_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, analyst_prev, analyst_curr, settings)
        assert alerts == []

    def test_does_not_fire_when_no_today_row(self):
        holding = _make_holding(ticker_yfinance="INFY.NS")
        analyst_prev = {"INFY.NS": {"rating": "HOLD", "target": 1800.0}}
        analyst_curr = {}  # no today data
        settings = {"alert_analyst_enabled": "true"}
        alerts = evaluate_alerts([holding], {}, analyst_prev, analyst_curr, settings)
        assert alerts == []


# ---------------------------------------------------------------------------
# Multiple holdings / empty settings
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_holdings(self):
        alerts = evaluate_alerts([], {}, {}, {}, {})
        assert alerts == []

    def test_empty_settings_fires_nothing(self):
        holding = _make_holding(current_price=2000.0, daily_pct=10.0, rsi_14=80.0)
        alerts = evaluate_alerts([holding], {}, {}, {}, {})
        assert alerts == []

    def test_multiple_holdings_multiple_alerts(self):
        h1 = _make_holding(ticker="HDFC", ticker_yfinance="HDFCBANK.NS", current_price=1600.0, rsi_14=75.0)
        h2 = _make_holding(ticker="INFY", ticker_yfinance="INFY.NS", current_price=1600.0, daily_pct=8.0, rsi_14=50.0)
        settings = {
            "alert_price_HDFCBANK.NS": "1500.0",
            "alert_price_HDFCBANK.NS_enabled": "true",
            "alert_daily_move_enabled": "true",
            "alert_daily_move_pct": "5.0",
            "alert_rsi_enabled": "true",
        }
        alerts = evaluate_alerts([h1, h2], {}, {}, {}, settings)
        types = [a["type"] for a in alerts]
        # h1 fires price + rsi; h2 fires daily_move
        assert "price" in types
        assert "rsi" in types
        assert "daily_move" in types
