"""
Tests for FastAPI endpoints (Plans 01 + 02 TDD).
"""
import io
import sqlite3
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# CSV content fixtures (inline — no disk files needed)
# ---------------------------------------------------------------------------

ZERODHA_CSV = (
    "Trading Symbol,Exchange,Quantity,Average Price,ISIN\n"
    "RELIANCE,NSE,10,2500.00,INE002A01018\n"
)

TR_CSV = (
    "Date,Type,Security name,ISIN,Quantity,Price per Unit,Total\n"
    "2024-01-15,Buy,SAP SE,DE0007164600,5,150.00,750.00\n"
)

ZERODHA_BAD_CSV = (
    "Exchange,Quantity,Average Price\n"
    "NSE,10,2500.00\n"
)


# ---------------------------------------------------------------------------
# Plan 01 tests (existing)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Plan 02 tests — POST /api/import
# ---------------------------------------------------------------------------

def test_import_zerodha_csv_endpoint(test_client):
    """POST /api/import with broker=zerodha + valid CSV → 200 with imported_count >= 1."""
    response = test_client.post(
        "/api/import",
        data={"broker": "zerodha"},
        files={"file": ("zerodha.csv", ZERODHA_CSV.encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "imported_count" in body
    assert body["imported_count"] >= 1


def test_import_trade_republic_csv_endpoint(test_client):
    """POST /api/import with broker=trade_republic + valid TR CSV → 200 with imported_count >= 1."""
    response = test_client.post(
        "/api/import",
        data={"broker": "trade_republic"},
        files={"file": ("tr.csv", TR_CSV.encode(), "text/csv")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "imported_count" in body
    assert body["imported_count"] >= 1


def test_import_invalid_broker(test_client):
    """POST /api/import with unknown broker → 400."""
    response = test_client.post(
        "/api/import",
        data={"broker": "unknown"},
        files={"file": ("file.csv", b"col1,col2\n1,2\n", "text/csv")},
    )
    assert response.status_code == 400


def test_import_bad_csv(test_client):
    """POST /api/import with Zerodha CSV missing required columns → 422 with error detail."""
    response = test_client.post(
        "/api/import",
        data={"broker": "zerodha"},
        files={"file": ("bad.csv", ZERODHA_BAD_CSV.encode(), "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    # Error detail should mention missing required columns
    detail_str = str(body).lower()
    assert "missing required columns" in detail_str


def test_portfolio_with_holdings_returns_pl(test_client):
    """After import, GET /api/portfolio has holdings with non-null pl/pl_pct; cash_by_broker present."""
    # Import Zerodha CSV first
    test_client.post(
        "/api/import",
        data={"broker": "zerodha"},
        files={"file": ("zerodha.csv", ZERODHA_CSV.encode(), "text/csv")},
    )

    response = test_client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert "cash_by_broker" in body
    # Holdings should be present
    assert len(body["holdings"]) >= 1
    # pl and pl_pct should be non-None (may be 0 when no price data)
    h = body["holdings"][0]
    assert h["pl"] is not None
    assert h["pl_pct"] is not None


def test_get_portfolio_structure(test_client):
    """GET /api/portfolio returns JSON with required top-level keys."""
    response = test_client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    for key in ("holdings", "total_inr", "total_eur", "cash_by_broker"):
        assert key in body, f"Missing key '{key}' in portfolio response"
    assert isinstance(body["total_inr"], (int, float))
    assert isinstance(body["total_eur"], (int, float))
    assert isinstance(body["cash_by_broker"], dict)
