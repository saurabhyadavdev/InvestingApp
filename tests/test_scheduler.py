"""
Tests for BriefingOrchestrator, APScheduler integration, and briefing/refresh endpoints.
Plan 04 — Task 1 (TDD RED).
"""
import json
import sqlite3
import pytest
import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_fetch_indices_result():
    return {
        "^NSEI":  {"symbol": "^NSEI",  "name": "Nifty 50", "close": 23456.78, "change_pct": 1.2,  "date": "2026-05-13", "market_label": "Nifty 50"},
        "^BSESN": {"symbol": "^BSESN", "name": "Sensex",   "close": 77000.0,  "change_pct": -0.5, "date": "2026-05-13", "market_label": "Sensex"},
        "^GDAXI": {"symbol": "^GDAXI", "name": "DAX",      "close": 18500.0,  "change_pct": 0.3,  "date": "2026-05-13", "market_label": "DAX"},
        "^GSPC":  {"symbol": "^GSPC",  "name": "S&P 500",  "close": 5300.0,   "change_pct": -0.1, "date": "2026-05-12", "market_label": "S&P 500"},
    }


def _mock_fetch_fx_result():
    return {"pair": "EURINR", "rate": 98.45, "low": 97.80, "high": 99.10, "timestamp": "2026-05-13T00:00:00+00:00"}


def _mock_portfolio_result():
    return {
        "holdings": [{"ticker": "RELIANCE", "quantity": 10, "avg_buy": 2500.0, "pl": 500.0, "pl_pct": 2.0, "currency": "INR", "broker": "zerodha"}],
        "total_inr": 500.0,
        "total_eur": 0.0,
        "cash_by_broker": {"zerodha": 0.0, "trade_republic": 0.0},
    }


# ---------------------------------------------------------------------------
# Test 1: BriefingOrchestrator.generate() assembles snapshot and stores to DB
# ---------------------------------------------------------------------------

def test_briefing_generate_creates_snapshot(db_path):
    """
    BriefingOrchestrator.generate() with mocked fetchers returns dict with required keys
    and inserts exactly 1 row into briefing_snapshots.
    """
    from backend.core.briefing import BriefingOrchestrator

    with patch("backend.core.briefing.DataFetcher") as MockDF, \
         patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

        MockDF.return_value.fetch_fx_rate.return_value = _mock_fetch_fx_result()
        MockDF.return_value.fetch_indices.return_value = _mock_fetch_indices_result()
        MockDF.return_value.fetch_holding_prices.return_value = {}
        MockDF.return_value.fetch_signals.return_value = {}
        MockDF.return_value.fetch_news.return_value = {"holdings": [], "india": [], "germany": [], "us": []}
        MockDF.return_value.fetch_analyst.return_value = {}
        mock_portfolio.return_value = _mock_portfolio_result()

        orchestrator = BriefingOrchestrator(db_path)
        result = orchestrator.generate()

    # Required keys in result
    required_keys = {"portfolio", "indices", "fx", "generated_at", "briefing_date"}
    for key in required_keys:
        assert key in result, f"Missing key '{key}' in briefing result"

    # generated_at should be UTC ISO 8601
    assert result["generated_at"].endswith("Z"), "generated_at should end with Z (UTC)"

    # briefing_date should be YYYY-MM-DD
    assert len(result["briefing_date"]) == 10
    assert result["briefing_date"][4] == "-"

    # Check DB has exactly 1 row
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM briefing_snapshots")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1, f"Expected 1 briefing_snapshot row, got {count}"


# ---------------------------------------------------------------------------
# Test 2: BriefingOrchestrator.get_latest() returns None on empty DB
# ---------------------------------------------------------------------------

def test_get_latest_returns_none_when_empty(db_path):
    """get_latest() returns None when briefing_snapshots table is empty."""
    from backend.core.briefing import BriefingOrchestrator

    orchestrator = BriefingOrchestrator(db_path)
    result = orchestrator.get_latest()
    assert result is None


# ---------------------------------------------------------------------------
# Test 3: GET /api/briefing with empty table returns 404
# ---------------------------------------------------------------------------

def test_get_briefing_endpoint_no_data(test_client, db_path):
    """GET /api/briefing with empty briefing_snapshots returns 404 with detail 'No briefing generated yet'."""
    import sqlite3 as _sqlite3
    # Wipe any rows inserted by startup auto-generation
    conn = _sqlite3.connect(db_path)
    conn.execute("DELETE FROM briefing_snapshots")
    conn.commit()
    conn.close()

    response = test_client.get("/api/briefing")
    assert response.status_code == 404
    body = response.json()
    assert "No briefing generated yet" in body.get("detail", "")


# ---------------------------------------------------------------------------
# Test 4: GET /api/briefing returns latest snapshot
# ---------------------------------------------------------------------------

def test_get_briefing_endpoint_returns_latest(test_client, db_path):
    """After inserting a briefing_snapshot row, GET /api/briefing returns 200 with briefing keys."""
    sample_briefing = {
        "portfolio": _mock_portfolio_result(),
        "indices": _mock_fetch_indices_result(),
        "fx": _mock_fetch_fx_result(),
        "generated_at": "2026-05-13T07:00:00Z",
        "briefing_date": "2026-05-13",
    }

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO briefing_snapshots (date, type, briefing_json) VALUES (?, ?, ?)",
        ("2026-05-13", "morning", json.dumps(sample_briefing)),
    )
    conn.commit()
    conn.close()

    response = test_client.get("/api/briefing")
    assert response.status_code == 200
    body = response.json()

    for key in ("portfolio", "indices", "fx", "generated_at"):
        assert key in body, f"Missing key '{key}' in /api/briefing response"


# ---------------------------------------------------------------------------
# Test 5: POST /api/refresh triggers generation and returns expected response
# ---------------------------------------------------------------------------

def test_refresh_endpoint_triggers_generation(test_client):
    """POST /api/refresh returns 200 with status='Briefing refreshed' and generated_at."""
    with patch("backend.api.refresh.BriefingOrchestrator") as MockOrch:
        MockOrch.return_value.generate.return_value = {
            "portfolio": _mock_portfolio_result(),
            "indices": _mock_fetch_indices_result(),
            "fx": _mock_fetch_fx_result(),
            "generated_at": "2026-05-13T10:00:00Z",
            "briefing_date": "2026-05-13",
        }
        response = test_client.post("/api/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "Briefing refreshed"
    assert "generated_at" in body


# ---------------------------------------------------------------------------
# Test 6: init_scheduler registers morning_briefing job at 07:00 Asia/Kolkata
# ---------------------------------------------------------------------------

def test_morning_briefing_job_registered(db_path):
    """init_scheduler(scheduler, db_path) registers job id='morning_briefing' at hour=7, tz=Asia/Kolkata."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from backend.scheduler import init_scheduler

    scheduler = BackgroundScheduler()
    init_scheduler(scheduler, db_path)

    job = scheduler.get_job("morning_briefing")
    assert job is not None, "Job 'morning_briefing' not found in scheduler"

    # Verify cron trigger properties
    trigger = job.trigger
    # CronTrigger fields are accessible via .fields
    field_map = {f.name: f for f in trigger.fields}
    assert "hour" in field_map
    hour_field = field_map["hour"]
    assert str(hour_field) == "7", f"Expected hour=7, got: {hour_field}"

    # Verify timezone is Asia/Kolkata
    tz_str = str(trigger.timezone)
    assert "Asia/Kolkata" in tz_str, f"Expected Asia/Kolkata timezone, got: {tz_str}"


# ---------------------------------------------------------------------------
# Test 7: Startup generates briefing when briefing_snapshots is empty
# ---------------------------------------------------------------------------

def test_startup_generates_briefing_if_missing(db_path):
    """If briefing_snapshots is empty on startup, generate() calls DataFetcher.fetch_indices."""
    from backend.core.briefing import BriefingOrchestrator

    with patch("backend.core.briefing.DataFetcher") as MockDF, \
         patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

        MockDF.return_value.fetch_fx_rate.return_value = _mock_fetch_fx_result()
        MockDF.return_value.fetch_indices.return_value = _mock_fetch_indices_result()
        MockDF.return_value.fetch_holding_prices.return_value = {}
        MockDF.return_value.fetch_signals.return_value = {}
        MockDF.return_value.fetch_news.return_value = {"holdings": [], "india": [], "germany": [], "us": []}
        MockDF.return_value.fetch_analyst.return_value = {}
        mock_portfolio.return_value = _mock_portfolio_result()

        orchestrator = BriefingOrchestrator(db_path)

        # Simulate startup behavior: check if empty, then generate
        latest = orchestrator.get_latest()
        assert latest is None  # DB is empty

        # Generate is called
        orchestrator.generate()

        # DataFetcher.fetch_indices should have been called at least once
        MockDF.return_value.fetch_indices.assert_called_at_least_once = True
        assert MockDF.return_value.fetch_indices.called, "fetch_indices was not called"
