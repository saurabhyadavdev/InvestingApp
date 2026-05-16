"""
Tests for DataFetcher.fetch_signals() — Plan 02-02 TDD Task 1.

Tests:
  1. fetch_signals returns dict with "AAPL" key having non-None rsi_14 (220-row mock data)
  2. Ticker with <15 rows returns all-None signals without raising
  3. Signals are cached to technical_indicators table
"""
import sqlite3
import sys
import os
from datetime import date
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_schema


def _make_multi_close_df(ticker: str, rows: int) -> pd.DataFrame:
    """
    Build a minimal yfinance multi-ticker style DataFrame with MultiIndex columns.
    Returns DataFrame with (Close, ticker) column and date index.
    """
    dates = pd.date_range("2024-01-01", periods=rows, freq="D", tz="UTC")
    # Synthetic close prices with some variance so indicators can be computed
    rng = np.random.default_rng(42)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, rows))
    df = pd.DataFrame(
        {("Close", ticker): closes},
        index=dates,
    )
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def _make_single_close_df(ticker: str, rows: int) -> pd.DataFrame:
    """Single-ticker flat DataFrame (as yfinance returns for one-ticker download)."""
    dates = pd.date_range("2024-01-01", periods=rows, freq="D", tz="UTC")
    rng = np.random.default_rng(42)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, rows))
    df = pd.DataFrame({"Close": closes}, index=dates)
    return df


class TestFetchSignals:
    """Unit tests for DataFetcher.fetch_signals()."""

    def test_fetch_signals_returns_rsi_for_valid_ticker(self, db_path):
        """
        With 220 rows of synthetic OHLCV, fetch_signals(["AAPL"]) returns a dict
        with key "AAPL" whose rsi_14 is a non-None float.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_df = _make_single_close_df("AAPL", 220)

        with patch("yfinance.download", return_value=mock_df):
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_signals(["AAPL"])

        assert "AAPL" in result, "Expected 'AAPL' key in result"
        assert result["AAPL"]["rsi_14"] is not None, "rsi_14 should be non-None for 220-row data"
        assert isinstance(result["AAPL"]["rsi_14"], float), "rsi_14 should be a float"

    def test_fetch_signals_insufficient_rows_returns_none_signals(self, db_path):
        """
        Ticker with <15 rows returns all-None signal values without raising.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_df = _make_single_close_df("AAPL", 10)

        with patch("yfinance.download", return_value=mock_df):
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_signals(["AAPL"])

        # Should not raise; AAPL entry should exist
        assert "AAPL" in result, "Expected 'AAPL' key even for insufficient data"
        sig = result["AAPL"]
        assert sig["rsi_14"] is None, "rsi_14 should be None for <15 rows"
        assert sig["macd"] is None, "macd should be None for <15 rows"
        assert sig["macd_signal"] is None, "macd_signal should be None for <15 rows"
        assert sig["macd_histogram"] is None, "macd_histogram should be None for <15 rows"
        assert sig["sma_50"] is None, "sma_50 should be None for <15 rows"
        assert sig["sma_200"] is None, "sma_200 should be None for <15 rows"

    def test_fetch_signals_partial_data_sma200_none(self, db_path):
        """
        With 100 rows: rsi_14 and macd computed, sma_200 is None (needs >=200 rows).
        """
        from backend.core.data_fetcher import DataFetcher

        mock_df = _make_single_close_df("AAPL", 100)

        with patch("yfinance.download", return_value=mock_df):
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_signals(["AAPL"])

        assert "AAPL" in result
        sig = result["AAPL"]
        assert sig["rsi_14"] is not None, "rsi_14 should be computed for 100 rows"
        assert sig["macd"] is not None, "macd should be computed for 100 rows"
        assert sig["sma_200"] is None, "sma_200 should be None for <200 rows"

    def test_fetch_signals_caches_to_db(self, db_path):
        """
        fetch_signals with 220 rows inserts a row into technical_indicators table.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_df = _make_single_close_df("AAPL", 220)

        with patch("yfinance.download", return_value=mock_df):
            fetcher = DataFetcher(db_path)
            fetcher.fetch_signals(["AAPL"])

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ticker, rsi_14 FROM technical_indicators WHERE ticker = ?",
            ("AAPL",),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None, "technical_indicators should have a row for AAPL"
        assert row[0] == "AAPL"
        assert row[1] is not None

    def test_fetch_signals_yfinance_failure_returns_empty(self, db_path):
        """
        If yfinance.download raises, fetch_signals returns {} without raising.
        """
        from backend.core.data_fetcher import DataFetcher

        with patch("yfinance.download", side_effect=Exception("network error")):
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_signals(["AAPL"])

        assert result == {}, "Should return empty dict on yfinance failure"

    def test_fetch_signals_result_has_all_keys(self, db_path):
        """
        Result dict for valid ticker has all 6 signal keys.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_df = _make_single_close_df("AAPL", 220)

        with patch("yfinance.download", return_value=mock_df):
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_signals(["AAPL"])

        expected_keys = {"rsi_14", "macd", "macd_signal", "macd_histogram", "sma_50", "sma_200"}
        assert set(result["AAPL"].keys()) == expected_keys
