"""
Tests for FastAPI endpoints (Plans 01 + 02 + 03 TDD).
"""
import io
import sqlite3
import pytest
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

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


# ---------------------------------------------------------------------------
# Plan 03 tests — timezone_utils (Task 1)
# ---------------------------------------------------------------------------

def test_market_reference_date_nse_before_close():
    """At 06:00 IST (before 15:30 close), get_market_reference_date('NSE') returns yesterday's date."""
    from backend.core.timezone_utils import get_market_reference_date
    # 06:00 IST = 00:30 UTC
    as_of = datetime(2026, 5, 13, 0, 30, 0, tzinfo=ZoneInfo("UTC"))
    result = get_market_reference_date("NSE", as_of=as_of)
    # Before close (15:30 IST), should return yesterday = 2026-05-12
    assert result == "2026-05-12"


def test_market_reference_date_nse_after_close():
    """At 17:00 IST (after 15:30 close), get_market_reference_date('NSE') returns today's date."""
    from backend.core.timezone_utils import get_market_reference_date
    # 17:00 IST = 11:30 UTC
    as_of = datetime(2026, 5, 13, 11, 30, 0, tzinfo=ZoneInfo("UTC"))
    result = get_market_reference_date("NSE", as_of=as_of)
    # After close (15:30 IST), should return today = 2026-05-13
    assert result == "2026-05-13"


def test_market_reference_date_unknown_market():
    """get_market_reference_date('UNKNOWN') raises ValueError."""
    from backend.core.timezone_utils import get_market_reference_date
    with pytest.raises(ValueError, match="Unknown market"):
        get_market_reference_date("UNKNOWN")


def _make_mock_download_result(symbols):
    """Create a minimal multi-ticker yfinance DataFrame mock with 2+ rows."""
    dates = pd.date_range("2026-05-12", periods=2, freq="D", tz="UTC")
    if len(symbols) == 1:
        # Single ticker: flat DataFrame
        df = pd.DataFrame({
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 100.0],
            "Close": [102.0, 103.0],
            "Adj Close": [102.0, 103.0],
            "Volume": [1000, 2000],
        }, index=dates)
    else:
        # Multi-ticker: MultiIndex columns (Field, Ticker)
        arrays = [
            ["Open", "Open", "High", "High", "Low", "Low", "Close", "Close", "Adj Close", "Adj Close", "Volume", "Volume"],
            symbols + symbols + symbols + symbols + symbols + symbols,
        ]
        cols = pd.MultiIndex.from_arrays(arrays)
        data = {
            ("Open", symbols[0]): [100.0, 101.0],
            ("Open", symbols[1]): [200.0, 201.0],
            ("High", symbols[0]): [105.0, 106.0],
            ("High", symbols[1]): [205.0, 206.0],
            ("Low", symbols[0]): [99.0, 100.0],
            ("Low", symbols[1]): [199.0, 200.0],
            ("Close", symbols[0]): [102.0, 103.0],
            ("Close", symbols[1]): [202.0, 203.0],
            ("Adj Close", symbols[0]): [102.0, 103.0],
            ("Adj Close", symbols[1]): [202.0, 203.0],
            ("Volume", symbols[0]): [1000, 2000],
            ("Volume", symbols[1]): [3000, 4000],
        }
        df = pd.DataFrame(data, index=dates)
    return df


def _make_mock_indices_download():
    """Create a 4-ticker mock DataFrame for indices fetch."""
    symbols = ["^NSEI", "^BSESN", "^GDAXI", "^GSPC"]
    dates = pd.date_range("2026-05-12", periods=2, freq="D", tz="UTC")
    data = {}
    for i, sym in enumerate(symbols):
        base = (i + 1) * 1000.0
        data[("Open", sym)] = [base, base + 10]
        data[("High", sym)] = [base + 20, base + 30]
        data[("Low", sym)] = [base - 10, base - 5]
        data[("Close", sym)] = [base + 5, base + 15]
        data[("Adj Close", sym)] = [base + 5, base + 15]
        data[("Volume", sym)] = [100000, 200000]
    df = pd.DataFrame(data, index=dates)
    return df


def test_indices_nifty_sensex(db_path):
    """DataFetcher.fetch_indices() returns entries for ^NSEI and ^BSESN with required keys."""
    from backend.core.data_fetcher import DataFetcher
    mock_df = _make_mock_indices_download()
    with patch("yfinance.download", return_value=mock_df):
        fetcher = DataFetcher(db_path)
        result = fetcher.fetch_indices()
    assert "^NSEI" in result
    assert "^BSESN" in result
    for sym in ["^NSEI", "^BSESN"]:
        entry = result[sym]
        assert isinstance(entry["close"], float)
        assert isinstance(entry["change_pct"], float)
        assert isinstance(entry["date"], str)
        assert isinstance(entry["market_label"], str)


def test_indices_dax(db_path):
    """DataFetcher.fetch_indices() returns entry for ^GDAXI with required keys."""
    from backend.core.data_fetcher import DataFetcher
    mock_df = _make_mock_indices_download()
    with patch("yfinance.download", return_value=mock_df):
        fetcher = DataFetcher(db_path)
        result = fetcher.fetch_indices()
    assert "^GDAXI" in result
    entry = result["^GDAXI"]
    assert isinstance(entry["close"], float)
    assert isinstance(entry["change_pct"], float)
    assert isinstance(entry["date"], str)
    assert isinstance(entry["market_label"], str)


def test_indices_sp500(db_path):
    """DataFetcher.fetch_indices() returns entry for ^GSPC with required keys."""
    from backend.core.data_fetcher import DataFetcher
    mock_df = _make_mock_indices_download()
    with patch("yfinance.download", return_value=mock_df):
        fetcher = DataFetcher(db_path)
        result = fetcher.fetch_indices()
    assert "^GSPC" in result
    entry = result["^GSPC"]
    assert isinstance(entry["close"], float)
    assert isinstance(entry["change_pct"], float)
    assert isinstance(entry["date"], str)
    assert isinstance(entry["market_label"], str)


def test_fx_rate_endpoint(db_path):
    """DataFetcher.fetch_fx_rate() returns dict with rate, low, high, pair, timestamp."""
    from backend.core.data_fetcher import DataFetcher
    # Mock yfinance.Ticker().history()
    mock_history = pd.DataFrame({
        "Open": [97.0, 98.0],
        "High": [99.5, 100.0],
        "Low": [96.0, 97.5],
        "Close": [98.0, 98.45],
        "Volume": [0, 0],
    }, index=pd.date_range("2026-05-12", periods=2, freq="D", tz="UTC"))

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_history

    with patch("yfinance.Ticker", return_value=mock_ticker):
        fetcher = DataFetcher(db_path)
        result = fetcher.fetch_fx_rate("EURINR=X")

    assert result["pair"] == "EURINR"
    assert isinstance(result["rate"], float)
    assert result["rate"] > 0
    assert isinstance(result["low"], float)
    assert isinstance(result["high"], float)
    assert isinstance(result["timestamp"], str)


def test_fx_range(db_path):
    """DataFetcher.fetch_fx_rate() returns low < high (valid range)."""
    from backend.core.data_fetcher import DataFetcher
    mock_history = pd.DataFrame({
        "Open": [97.0],
        "High": [99.5],
        "Low": [96.0],
        "Close": [98.45],
        "Volume": [0],
    }, index=pd.date_range("2026-05-13", periods=1, freq="D", tz="UTC"))

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_history

    with patch("yfinance.Ticker", return_value=mock_ticker):
        fetcher = DataFetcher(db_path)
        result = fetcher.fetch_fx_rate("EURINR=X")

    assert result["low"] < result["high"], "FX low should be less than high"
