"""
Tests for backend/api/alerts.py

Covers:
  - POST saves the expected keys to the settings table
  - POST does NOT touch fx_alert_threshold (seeded before POST)
  - GET round-trips the saved values back in the same shape as POST body
"""
import sqlite3
import tempfile
import os
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.alerts import router


# ---------------------------------------------------------------------------
# Test app + client setup
# ---------------------------------------------------------------------------

def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def db_path(tmp_path):
    """Create a temp SQLite DB with the settings table."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Seed fx_alert_threshold — must survive alert saves
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("fx_alert_threshold", "99.5"),
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def client(db_path):
    app = _make_app()
    # Patch the config settings to use the temp DB
    with patch("backend.api.alerts.config_settings") as mock_settings:
        mock_settings.DB_PATH = db_path
        with TestClient(app) as c:
            yield c, db_path


# ---------------------------------------------------------------------------
# POST /api/alerts
# ---------------------------------------------------------------------------

class TestSaveAlerts:
    def test_post_saves_price_target(self, client):
        c, db_path = client
        payload = {
            "price_targets": {"HDFCBANK.NS": 1500.0},
            "price_enabled": {"HDFCBANK.NS": True},
            "daily_move_pct": 5.0,
            "daily_move_enabled": True,
            "rsi_enabled": True,
            "analyst_enabled": False,
        }
        resp = c.post("/api/alerts", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

        # Verify keys written to DB
        conn = sqlite3.connect(db_path)
        rows = dict(conn.execute("SELECT key, value FROM settings").fetchall())
        conn.close()

        assert rows.get("alert_price_HDFCBANK.NS") == "1500.0"
        assert rows.get("alert_price_HDFCBANK.NS_enabled") == "true"
        assert rows.get("alert_daily_move_pct") == "5.0"
        assert rows.get("alert_daily_move_enabled") == "true"
        assert rows.get("alert_rsi_enabled") == "true"
        assert rows.get("alert_analyst_enabled") == "false"

    def test_post_does_not_clobber_fx_alert_threshold(self, client):
        """
        Critical: fx_alert_threshold MUST NOT be modified by the alerts endpoint.
        """
        c, db_path = client
        payload = {
            "price_targets": {"INFY.NS": 2000.0},
            "price_enabled": {"INFY.NS": True},
            "daily_move_pct": 3.0,
            "daily_move_enabled": False,
            "rsi_enabled": False,
            "analyst_enabled": True,
        }
        resp = c.post("/api/alerts", json=payload)
        assert resp.status_code == 200

        # fx_alert_threshold must still be 99.5
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", ("fx_alert_threshold",)
        ).fetchone()
        conn.close()

        assert row is not None, "fx_alert_threshold row was deleted!"
        assert row[0] == "99.5", f"fx_alert_threshold changed to {row[0]}"

    def test_post_with_empty_price_targets(self, client):
        c, _ = client
        payload = {
            "price_targets": {},
            "price_enabled": {},
            "daily_move_pct": 5.0,
            "daily_move_enabled": True,
            "rsi_enabled": False,
            "analyst_enabled": False,
        }
        resp = c.post("/api/alerts", json=payload)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------

class TestGetAlerts:
    def test_get_round_trips_saved_values(self, client):
        """POST then GET should return the same values."""
        c, _ = client
        payload = {
            "price_targets": {"HDFCBANK.NS": 1500.0, "INFY.NS": 2000.0},
            "price_enabled": {"HDFCBANK.NS": True, "INFY.NS": False},
            "daily_move_pct": 7.5,
            "daily_move_enabled": True,
            "rsi_enabled": True,
            "analyst_enabled": True,
        }
        post_resp = c.post("/api/alerts", json=payload)
        assert post_resp.json()["ok"] is True

        get_resp = c.get("/api/alerts")
        assert get_resp.status_code == 200
        data = get_resp.json()

        assert data["price_targets"].get("HDFCBANK.NS") == pytest.approx(1500.0)
        assert data["price_targets"].get("INFY.NS") == pytest.approx(2000.0)
        assert data["price_enabled"].get("HDFCBANK.NS") is True
        assert data["price_enabled"].get("INFY.NS") is False
        assert data["daily_move_pct"] == pytest.approx(7.5)
        assert data["daily_move_enabled"] is True
        assert data["rsi_enabled"] is True
        assert data["analyst_enabled"] is True

    def test_get_does_not_include_fx_alert_threshold(self, client):
        """fx_alert_threshold must NOT appear in the GET response."""
        c, _ = client
        resp = c.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        # Check top-level keys — fx_alert_threshold must not be present
        assert "fx_alert_threshold" not in data
        # Also check nested dicts
        for key in (data.get("price_targets") or {}).keys():
            assert key != "fx_alert_threshold"

    def test_get_returns_defaults_when_no_settings(self, client):
        """GET should return sensible defaults when no alert keys exist."""
        c, _ = client
        resp = c.get("/api/alerts")
        data = resp.json()
        # Even with only fx_alert_threshold in DB, GET should return defaults
        assert isinstance(data["price_targets"], dict)
        assert isinstance(data["rsi_enabled"], bool)
        assert isinstance(data["daily_move_pct"], (int, float))
