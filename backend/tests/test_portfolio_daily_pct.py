"""
Unit tests for compute_daily_pct in backend.core.portfolio.

Tests use a temporary SQLite database with the price_history schema.
"""
import sqlite3
import tempfile
import os

import pytest

from backend.core.portfolio import compute_daily_pct


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_db(rows: list[tuple]) -> str:
    """
    Create a temp SQLite DB with price_history table and seed with rows.

    Each row in `rows` is a (ticker, date, close) tuple.
    Returns the db_path.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        )
    """)
    for ticker, date, close in rows:
        conn.execute(
            "INSERT INTO price_history (ticker, date, close) VALUES (?, ?, ?)",
            (ticker, date, close),
        )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeDailyPct:
    """Tests for compute_daily_pct()."""

    def test_positive_change(self):
        """Two rows where today's close is higher than yesterday's returns positive %."""
        db = _make_db([
            ("HDFC.NS", "2026-05-14", 100.0),
            ("HDFC.NS", "2026-05-15", 105.0),
        ])
        try:
            result = compute_daily_pct(db, "HDFC.NS")
            assert result is not None
            assert abs(result - 5.0) < 1e-9
        finally:
            os.unlink(db)

    def test_negative_change(self):
        """Two rows where today's close is lower than yesterday's returns negative %."""
        db = _make_db([
            ("INFY.NS", "2026-05-14", 200.0),
            ("INFY.NS", "2026-05-15", 190.0),
        ])
        try:
            result = compute_daily_pct(db, "INFY.NS")
            assert result is not None
            assert abs(result - (-5.0)) < 1e-9
        finally:
            os.unlink(db)

    def test_single_row_returns_none(self):
        """Only one row in price_history — insufficient for daily % change."""
        db = _make_db([
            ("AAVAS.NS", "2026-05-15", 100.0),
        ])
        try:
            result = compute_daily_pct(db, "AAVAS.NS")
            assert result is None
        finally:
            os.unlink(db)

    def test_zero_rows_returns_none(self):
        """Ticker not in price_history at all returns None."""
        db = _make_db([])
        try:
            result = compute_daily_pct(db, "UNKNOWN.NS")
            assert result is None
        finally:
            os.unlink(db)

    def test_zero_prev_close_returns_none(self):
        """Previous close is 0 — division by zero guard returns None."""
        db = _make_db([
            ("ZEROCLOSE.NS", "2026-05-14", 0.0),
            ("ZEROCLOSE.NS", "2026-05-15", 10.0),
        ])
        try:
            result = compute_daily_pct(db, "ZEROCLOSE.NS")
            assert result is None
        finally:
            os.unlink(db)

    def test_missing_ticker_returns_none(self):
        """Empty-string or None ticker returns None without error."""
        db = _make_db([
            ("HDFC.NS", "2026-05-14", 100.0),
            ("HDFC.NS", "2026-05-15", 105.0),
        ])
        try:
            assert compute_daily_pct(db, "") is None
            assert compute_daily_pct(db, None) is None
        finally:
            os.unlink(db)

    def test_correct_row_order_used(self):
        """Rows are selected by date DESC so most recent is treated as today."""
        db = _make_db([
            # Insert in non-chronological order to confirm ORDER BY date DESC LIMIT 2 is correct
            ("TCS.NS", "2026-05-15", 3500.0),   # today
            ("TCS.NS", "2026-05-13", 3200.0),   # two days ago
            ("TCS.NS", "2026-05-14", 3400.0),   # yesterday
        ])
        try:
            # Expected: (3500 - 3400) / 3400 * 100 = 2.941...
            result = compute_daily_pct(db, "TCS.NS")
            assert result is not None
            expected = (3500.0 - 3400.0) / 3400.0 * 100
            assert abs(result - expected) < 1e-9
        finally:
            os.unlink(db)
