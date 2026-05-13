"""
Tests for backend/core/portfolio.py (Task 1 TDD).
All CSV parsing tests use io.StringIO — no disk access for CSV content.
"""
import io
import sqlite3
import tempfile
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_schema


# ---------------------------------------------------------------------------
# Sample CSV fixtures
# ---------------------------------------------------------------------------

ZERODHA_CSV_VALID = (
    "Trading Symbol,Exchange,Quantity,Average Price,ISIN\n"
    "RELIANCE,NSE,10,2500.00,INE002A01018\n"
)

ZERODHA_CSV_MISSING_COL = (
    "Exchange,Quantity,Average Price,ISIN\n"
    "NSE,10,2500.00,INE002A01018\n"
)

TR_CSV_VALID = (
    "Date,Type,Security name,ISIN,Quantity,Price per Unit,Total\n"
    "2024-01-15,Buy,SAP SE,DE0007164600,5,150.00,750.00\n"
    "2024-01-20,Buy,Vanguard FTSE All-World ETF,IE00B3RBWM25,10,95.00,950.00\n"
)

TR_CSV_MIXED = (
    "Date,Type,Security name,ISIN,Quantity,Price per Unit,Total\n"
    "2024-01-10,Buy,SAP SE,DE0007164600,10,140.00,1400.00\n"
    "2024-01-15,Buy,SAP SE,DE0007164600,5,150.00,750.00\n"
    "2024-01-20,Sell,SAP SE,DE0007164600,8,160.00,1280.00\n"
)


# ---------------------------------------------------------------------------
# Helper: in-memory DB with schema
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite DB with Phase 1 schema."""
    path = str(tmp_path / "test.db")
    create_schema(path)
    return path


# ---------------------------------------------------------------------------
# Test 1: Zerodha CSV import basics
# ---------------------------------------------------------------------------

def test_zerodha_import(tmp_db):
    """Parse Zerodha CSV → one holding with correct fields."""
    from backend.core.portfolio import import_zerodha_csv

    count = import_zerodha_csv(io.StringIO(ZERODHA_CSV_VALID), tmp_db)
    assert count >= 1

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM holdings WHERE broker='zerodha'")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1
    h = rows[0]
    assert h["broker"] == "zerodha"
    assert h["currency"] == "INR"
    assert h["region"] == "india"
    assert h["ticker_yfinance"].endswith(".NS")
    assert h["units"] > 0


# ---------------------------------------------------------------------------
# Test 2: Trade Republic CSV import basics
# ---------------------------------------------------------------------------

def test_trade_republic_import(tmp_db):
    """Parse TR CSV → holdings with correct fields."""
    from backend.core.portfolio import import_trade_republic_csv

    count = import_trade_republic_csv(io.StringIO(TR_CSV_VALID), tmp_db)
    assert count >= 1

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM holdings WHERE broker='trade_republic'")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) >= 1
    h = rows[0]
    assert h["broker"] == "trade_republic"
    assert h["currency"] == "EUR"
    assert h["units"] > 0


# ---------------------------------------------------------------------------
# Test 3: P&L calculation
# ---------------------------------------------------------------------------

def test_pl_calculation(tmp_db):
    """get_portfolio_with_pl calculates pl and pl_pct correctly."""
    from backend.core.portfolio import get_portfolio_with_pl

    # Seed a holding directly
    conn = sqlite3.connect(tmp_db)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO holdings
            (broker, ticker_local, ticker_yfinance, isin, units, cost_per_unit, currency, region, asset_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("zerodha", "INFY", "INFY.NS", "INE009A01021", 10, 120.0, "INR", "india", "equity"))
    # Insert a price row
    cur.execute("""
        INSERT INTO price_history (ticker, date, close, adj_close) VALUES (?, ?, ?, ?)
    """, ("INFY.NS", "2024-06-01", 130.0, 130.0))
    conn.commit()
    conn.close()

    result = get_portfolio_with_pl(tmp_db)
    holdings = result["holdings"]
    assert len(holdings) == 1
    h = holdings[0]
    # pl = (130 - 120) * 10 = 100
    assert h["pl"] == pytest.approx(100.0, abs=0.01)
    # pl_pct = 100 / (120 * 10) * 100 = 8.33
    assert h["pl_pct"] == pytest.approx(8.33, abs=0.01)


# ---------------------------------------------------------------------------
# Test 4: Missing required column raises ValueError
# ---------------------------------------------------------------------------

def test_zerodha_missing_required_col(tmp_db):
    """CSV missing 'Trading Symbol' raises ValueError with descriptive message."""
    from backend.core.portfolio import import_zerodha_csv

    with pytest.raises(ValueError, match="missing required columns"):
        import_zerodha_csv(io.StringIO(ZERODHA_CSV_MISSING_COL), tmp_db)


# ---------------------------------------------------------------------------
# Test 5: Region classification for India
# ---------------------------------------------------------------------------

def test_region_classification_india(tmp_db):
    """Exchange=NSE → region='india', asset_type='equity'."""
    from backend.core.portfolio import import_zerodha_csv

    import_zerodha_csv(io.StringIO(ZERODHA_CSV_VALID), tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT region, asset_type FROM holdings WHERE broker='zerodha'")
    row = cur.fetchone()
    conn.close()

    assert row["region"] == "india"
    assert row["asset_type"] == "equity"


# ---------------------------------------------------------------------------
# Test 6: ETF classification from Security name
# ---------------------------------------------------------------------------

def test_region_classification_etf(tmp_db):
    """TR row with 'ETF' in Security name → asset_type='etf'."""
    from backend.core.portfolio import import_trade_republic_csv

    import_trade_republic_csv(io.StringIO(TR_CSV_VALID), tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # The Vanguard ETF row should be asset_type=etf
    cur.execute("SELECT asset_type FROM holdings WHERE isin='IE00B3RBWM25'")
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row["asset_type"] == "etf"


# ---------------------------------------------------------------------------
# Test 7: Cash balance parsing
# ---------------------------------------------------------------------------

def test_cash_balance_parse(tmp_db):
    """Zerodha CSV with CASHCOMPONENT ticker → asset_type='cash'."""
    from backend.core.portfolio import import_zerodha_csv

    cash_csv = (
        "Trading Symbol,Exchange,Quantity,Average Price,ISIN\n"
        "CASHCOMPONENT,NSE,0,0,\n"
    )
    # Should not raise; cash rows get asset_type='cash'
    import_zerodha_csv(io.StringIO(cash_csv), tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT asset_type FROM holdings WHERE ticker_local='CASHCOMPONENT'")
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row["asset_type"] == "cash"
