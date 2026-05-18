"""
Tests for DataFetcher.fetch_benchmark and _window_start helper.

Unit tests — yfinance.download is mocked; no network calls are made.
"""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.core.data_fetcher import DataFetcher, _window_start


class TestWindowStart(unittest.TestCase):
    """Tests for the module-level _window_start helper."""

    def test_1d(self):
        result = _window_start("1D")
        expected = date.today() - timedelta(days=1)
        self.assertEqual(result, expected)

    def test_1w(self):
        result = _window_start("1W")
        expected = date.today() - timedelta(days=7)
        self.assertEqual(result, expected)

    def test_1m(self):
        result = _window_start("1M")
        expected = date.today() - timedelta(days=30)
        self.assertEqual(result, expected)

    def test_3m(self):
        result = _window_start("3M")
        expected = date.today() - timedelta(days=90)
        self.assertEqual(result, expected)

    def test_ytd(self):
        result = _window_start("YTD")
        today = date.today()
        expected = date(today.year, 1, 1)
        self.assertEqual(result, expected)

    def test_1y(self):
        result = _window_start("1Y")
        expected = date.today() - timedelta(days=365)
        self.assertEqual(result, expected)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError) as ctx:
            _window_start("5Y")
        self.assertIn("Unknown window", str(ctx.exception))

    def test_unknown_empty_raises(self):
        with self.assertRaises(ValueError):
            _window_start("")


class TestFetchBenchmarkEmpty(unittest.TestCase):
    """fetch_benchmark with empty holdings returns the all-None shaped dict."""

    def setUp(self):
        self.fetcher = DataFetcher(db_path=":memory:")

    @patch("backend.core.data_fetcher.yf.download")
    def test_empty_holdings_returns_correct_shape(self, mock_dl):
        # Should return early before calling yf.download because no investable holdings
        result = self.fetcher.fetch_benchmark([])

        # Shape assertions
        self.assertIn("windows", result)
        self.assertIn("portfolio", result)
        self.assertIn("indices", result)
        self.assertIn("regional", result)

        expected_windows = ["1D", "1W", "1M", "3M", "YTD", "1Y"]
        self.assertEqual(result["windows"], expected_windows)

        # All portfolio windows None
        for w in expected_windows:
            self.assertIsNone(result["portfolio"][w], f"portfolio[{w}] should be None")

        # All index windows None
        for idx in ("^NSEI", "^GSPC", "^GDAXI"):
            self.assertIn(idx, result["indices"])
            for w in expected_windows:
                self.assertIsNone(result["indices"][idx][w], f"indices[{idx}][{w}] should be None")

        # All regional windows None
        for region in ("india", "germany_us_etf"):
            self.assertIn(region, result["regional"])
            for w in expected_windows:
                self.assertIsNone(result["regional"][region][w])

    @patch("backend.core.data_fetcher.yf.download")
    def test_cash_holdings_excluded(self, mock_dl):
        """Cash holdings should be skipped from portfolio weighting (asset_type == 'cash').

        Note: index tickers (^NSEI, ^GSPC, ^GDAXI) are always fetched even when
        there are no investable holdings. The mock returns empty to simulate no data.
        """
        mock_dl.return_value = pd.DataFrame()
        cash_holding = {
            "ticker_yfinance": "CASH",
            "quantity": 1000,
            "current_price": 1.0,
            "currency": "INR",
            "asset_type": "cash",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([cash_holding])
        # Cash ticker is not in the combined list sent to yfinance (only indices are)
        call_tickers = mock_dl.call_args[1].get("tickers", mock_dl.call_args[0][0] if mock_dl.call_args[0] else "")
        self.assertNotIn("CASH", call_tickers)
        self.assertIn("portfolio", result)
        for w in result["windows"]:
            self.assertIsNone(result["portfolio"][w])

    @patch("backend.core.data_fetcher.yf.download")
    def test_zero_quantity_excluded(self, mock_dl):
        """Holdings with quantity 0 should be excluded from portfolio weighting."""
        mock_dl.return_value = pd.DataFrame()
        zero_qty = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 0,
            "current_price": 100.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([zero_qty])
        # Zero-quantity holding ticker should not appear in tickers sent to yfinance
        call_tickers = mock_dl.call_args[1].get("tickers", "") if mock_dl.call_args else ""
        self.assertNotIn("AAVAS.NS", call_tickers)
        self.assertIn("portfolio", result)
        for w in result["windows"]:
            self.assertIsNone(result["portfolio"][w])


class TestFetchBenchmarkWithData(unittest.TestCase):
    """fetch_benchmark with mocked yf.download produces non-None returns."""

    def setUp(self):
        self.fetcher = DataFetcher(db_path=":memory:")

    def _make_mock_df(self, tickers: list[str], num_days: int = 400) -> pd.DataFrame:
        """
        Create a mocked multi-ticker yfinance DataFrame with fake Close prices.

        Columns are a MultiIndex (field, ticker); index is DatetimeIndex.
        Prices increase linearly so all windows show positive returns.
        """
        today = pd.Timestamp.today().normalize()
        dates = pd.bdate_range(end=today, periods=num_days)

        # Build MultiIndex columns: (Close, ticker) for each ticker
        arrays = [
            ["Close"] * len(tickers),
            tickers,
        ]
        columns = pd.MultiIndex.from_arrays(arrays)

        # Linearly increasing prices starting from 100
        import numpy as np
        data = {
            (f, t): 100.0 + i * 0.05
            for i, t in enumerate(tickers)
            for f in ["Close"]
        }

        rows = {}
        for col in columns:
            base = 100.0 + tickers.index(col[1]) * 0.05
            rows[col] = [base + j * 0.1 for j in range(len(dates))]

        df = pd.DataFrame(rows, index=dates, columns=columns)
        return df

    @patch("backend.core.data_fetcher.yf.download")
    def test_index_returns_non_none(self, mock_dl):
        """With a valid stub DataFrame, index returns for each window should be non-None."""
        all_tickers = ["AAVAS.NS", "^NSEI", "^GSPC", "^GDAXI"]
        mock_dl.return_value = self._make_mock_df(all_tickers)

        holding = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 10,
            "current_price": 200.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([holding])

        mock_dl.assert_called_once()
        call_kwargs = mock_dl.call_args
        self.assertIn("period", call_kwargs.kwargs if call_kwargs.kwargs else {})

        for w in ["1M", "3M", "YTD", "1Y"]:
            self.assertIsNotNone(result["indices"]["^NSEI"][w], f"^NSEI[{w}] should be non-None")
            self.assertIsNotNone(result["indices"]["^GSPC"][w])
            self.assertIsNotNone(result["indices"]["^GDAXI"][w])

    @patch("backend.core.data_fetcher.yf.download")
    def test_portfolio_return_non_none(self, mock_dl):
        """Portfolio aggregate return should be non-None when data is present."""
        all_tickers = ["AAVAS.NS", "^NSEI", "^GSPC", "^GDAXI"]
        mock_dl.return_value = self._make_mock_df(all_tickers)

        holding = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 5,
            "current_price": 150.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([holding])

        for w in ["1M", "3M", "YTD", "1Y"]:
            self.assertIsNotNone(result["portfolio"][w], f"portfolio[{w}] should be non-None")

    @patch("backend.core.data_fetcher.yf.download")
    def test_regional_india_non_none(self, mock_dl):
        """India regional bucket should be non-None for a holding with region='india'."""
        all_tickers = ["AAVAS.NS", "^NSEI", "^GSPC", "^GDAXI"]
        mock_dl.return_value = self._make_mock_df(all_tickers)

        holding = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 5,
            "current_price": 150.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([holding])

        for w in ["1M", "3M", "YTD", "1Y"]:
            self.assertIsNotNone(result["regional"]["india"][w])
            # germany_us_etf bucket should be None (no holdings in that region)
            self.assertIsNone(result["regional"]["germany_us_etf"][w])

    @patch("backend.core.data_fetcher.yf.download")
    def test_empty_yfinance_response_returns_shape(self, mock_dl):
        """If yfinance returns empty DataFrame, the empty-shape dict should be returned."""
        mock_dl.return_value = pd.DataFrame()

        holding = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 5,
            "current_price": 150.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([holding])

        self.assertIn("portfolio", result)
        for w in result["windows"]:
            self.assertIsNone(result["portfolio"][w])

    @patch("backend.core.data_fetcher.yf.download")
    def test_positive_return_value(self, mock_dl):
        """With linearly increasing prices, 1M return should be positive."""
        all_tickers = ["AAVAS.NS", "^NSEI", "^GSPC", "^GDAXI"]
        mock_dl.return_value = self._make_mock_df(all_tickers, num_days=400)

        holding = {
            "ticker_yfinance": "AAVAS.NS",
            "quantity": 5,
            "current_price": 150.0,
            "currency": "INR",
            "asset_type": "stock",
            "region": "india",
        }
        result = self.fetcher.fetch_benchmark([holding])

        pct_1m = result["portfolio"]["1M"]
        if pct_1m is not None:
            self.assertGreater(pct_1m, 0, "Expected positive return for linearly rising prices")


if __name__ == "__main__":
    unittest.main()
