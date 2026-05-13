"""
Tests for database schema creation and config (Task 1 TDD).
"""
import sqlite3
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_schema
from backend.config import Settings


def test_schema_creates_all_tables(tmp_path):
    """After calling create_schema(), all 7 tables must exist."""
    db = str(tmp_path / "test.db")
    create_schema(db)

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected = {
        "holdings",
        "price_history",
        "technical_indicators",
        "fx_rates",
        "briefing_snapshots",
        "settings",
        "chat_history",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_holdings_table_columns(tmp_path):
    """holdings table must have all required columns."""
    db = str(tmp_path / "test.db")
    create_schema(db)

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(holdings)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    required = {
        "id",
        "broker",
        "ticker_local",
        "isin",
        "ticker_yfinance",
        "name",
        "units",
        "cost_per_unit",
        "currency",
        "region",
        "asset_type",
        "updated_at",
    }
    assert required.issubset(columns), f"Missing columns: {required - columns}"


def test_config_loads_db_path():
    """Config.DB_PATH must return a string ending in 'app.db' by default."""
    s = Settings()
    assert s.DB_PATH.endswith("app.db"), f"DB_PATH is '{s.DB_PATH}', expected to end with 'app.db'"
