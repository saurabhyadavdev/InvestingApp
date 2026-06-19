import os
import sqlite3
import sys
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _daily_prices() -> pd.DataFrame:
    dates = pd.date_range("2026-05-27", periods=2, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [99.0, 104.0],
            "High": [101.0, 106.0],
            "Low": [98.0, 103.0],
            "Close": [100.0, 105.0],
            "Adj Close": [100.0, 105.0],
            "Volume": [1000, 1200],
        },
        index=dates,
    )


class _FakeFastInfo:
    """Minimal stand-in for yfinance FastInfo supporting dict-style access."""

    def __init__(self, last_price):
        self._last_price = last_price

    def __getitem__(self, key):
        if key == "lastPrice":
            return self._last_price
        raise KeyError(key)


def test_fetch_holding_prices_overlays_live_price(db_path):
    """Current price should be the authoritative fast_info last price (auction-aware),
    overlaid onto the current session row without overwriting the previous daily close."""
    from backend.core.data_fetcher import DataFetcher

    fake_ticker = type("T", (), {"fast_info": _FakeFastInfo(111.0)})()

    with patch("yfinance.download", return_value=_daily_prices()), \
         patch("yfinance.Ticker", return_value=fake_ticker), \
         patch("backend.core.data_fetcher._current_session_date", return_value="2026-05-29"):
        result = DataFetcher(db_path).fetch_holding_prices(["AAPL"])

    assert result["AAPL"] == pytest.approx(111.0)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT date, close FROM price_history WHERE ticker = ? ORDER BY date DESC",
            ("AAPL",),
        ).fetchall()
    finally:
        conn.close()

    assert rows[0] == ("2026-05-29", 111.0)        # live overlay on current session
    assert ("2026-05-28", 105.0) in rows           # previous daily close preserved


def test_portfolio_holding_includes_price_fetched_at(db_path):
    """Portfolio rows should expose when the displayed price was fetched."""
    from backend.core.portfolio import get_portfolio_with_pl

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO holdings
                (broker, ticker_local, ticker_yfinance, isin, units, cost_per_unit, currency, region, asset_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("zerodha", "AAPL", "AAPL", "US0378331005", 2, 100.0, "USD", "us", "equity"),
        )
        conn.execute(
            """
            INSERT INTO price_history (ticker, date, close, adj_close, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("AAPL", "2026-05-29", 111.0, 111.0, "2026-05-29 06:55:13"),
        )
        conn.commit()
    finally:
        conn.close()

    result = get_portfolio_with_pl(db_path)
    holding = result["holdings"][0]

    assert holding["current_price"] == pytest.approx(111.0)
    assert holding["price_date"] == "2026-05-29"
    assert holding["price_fetched_at"] == "2026-05-29 06:55:13"
