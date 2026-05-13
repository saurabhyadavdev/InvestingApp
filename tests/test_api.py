"""
Tests for FastAPI endpoints (Task 2 TDD).
"""
import sqlite3
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_health_returns_200(test_client):
    """GET /health returns 200 with JSON body containing 'status': 'ok'."""
    response = test_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


def test_portfolio_empty_returns_200(test_client):
    """GET /api/portfolio with empty DB returns 200 with 'holdings' as empty list."""
    response = test_client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert "holdings" in body
    assert isinstance(body["holdings"], list)
    assert len(body["holdings"]) == 0


def test_portfolio_returns_holdings(test_client, db_path):
    """
    After INSERT into holdings table, GET /api/portfolio returns 200
    with holdings array of length >= 1 containing expected keys.
    """
    # Insert a sample holding directly into the test DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO holdings
            (broker, ticker_local, isin, ticker_yfinance, name, units, cost_per_unit, currency, region, asset_type)
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "zerodha",
        "RELIANCE",
        "INE002A01018",
        "RELIANCE.NS",
        "Reliance Industries",
        100.0,
        2500.0,
        "INR",
        "india",
        "equity",
    ))
    conn.commit()
    conn.close()

    response = test_client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert "holdings" in body
    assert len(body["holdings"]) >= 1

    holding = body["holdings"][0]
    expected_keys = {"ticker", "isin", "quantity", "avg_buy", "current_price", "pl", "pl_pct", "currency", "region", "broker"}
    for key in expected_keys:
        assert key in holding, f"Missing key '{key}' in holding response"
