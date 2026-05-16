"""
Tests for DataFetcher.fetch_news() and BriefingOrchestrator.generate() news/signals steps.
Plan 02-02 TDD Task 2.

Tests:
  1. fetch_news returns empty dict for all tabs when NEWSAPI_KEY is unset
  2. fetch_news returns correct structure with articles when mocked NewsAPI succeeds
  3. fetch_news uses date-keyed cache (no API call on second call same day)
  4. fetch_news handles individual tab failure gracefully (empty list for failed tab)
  5. generate() includes "news" key in returned briefing dict
  6. generate() merges signals into holdings (rsi_14 present per holding)
"""
import json
import sqlite3
import sys
import os
from datetime import date
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import create_schema


def _mock_newsapi_response(articles=None):
    """Build a mock NewsApiClient.get_everything() response."""
    if articles is None:
        articles = [
            {
                "title": "Test Article",
                "url": "https://example.com/article",
                "source": {"name": "Test Source"},
                "publishedAt": "2026-05-16T08:00:00Z",
            }
        ]
    return {"status": "ok", "totalResults": len(articles), "articles": articles}


class TestFetchNews:
    """Unit tests for DataFetcher.fetch_news()."""

    def test_fetch_news_empty_key_returns_empty(self, db_path):
        """
        When NEWSAPI_KEY is empty, fetch_news returns all-empty tabs without calling NewsAPI.
        """
        from backend.core.data_fetcher import DataFetcher

        with patch("backend.core.data_fetcher.settings") as mock_settings:
            mock_settings.NEWSAPI_KEY = ""
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_news(["AAPL"], ["Apple Inc"])

        assert result == {"holdings": [], "india": [], "germany": [], "us": []}

    def test_fetch_news_returns_correct_structure(self, db_path):
        """
        With mocked NewsAPI returning 1 article per tab, fetch_news returns dict with
        4 keys each containing lists of article dicts with title, url, source, time_ago.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_client = MagicMock()
        mock_client.get_everything.return_value = _mock_newsapi_response()

        with patch("backend.core.data_fetcher.settings") as mock_settings, \
             patch("backend.core.data_fetcher.NewsApiClient", return_value=mock_client):
            mock_settings.NEWSAPI_KEY = "test_key_123"
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_news(["AAPL"], ["Apple Inc"])

        assert set(result.keys()) == {"holdings", "india", "germany", "us"}
        for tab in ("holdings", "india", "germany", "us"):
            assert isinstance(result[tab], list), f"{tab} should be a list"
            if result[tab]:
                article = result[tab][0]
                assert "title" in article, f"article missing 'title' in tab {tab}"
                assert "url" in article, f"article missing 'url' in tab {tab}"
                assert "source" in article, f"article missing 'source' in tab {tab}"
                assert "time_ago" in article, f"article missing 'time_ago' in tab {tab}"

    def test_fetch_news_caches_result(self, db_path):
        """
        After first fetch_news call, a second call for the same date should use cache
        without calling NewsAPI again.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_client = MagicMock()
        mock_client.get_everything.return_value = _mock_newsapi_response()

        with patch("backend.core.data_fetcher.settings") as mock_settings, \
             patch("backend.core.data_fetcher.NewsApiClient", return_value=mock_client):
            mock_settings.NEWSAPI_KEY = "test_key_123"
            fetcher = DataFetcher(db_path)
            result1 = fetcher.fetch_news(["AAPL"], ["Apple Inc"])
            # Reset call count
            first_call_count = mock_client.get_everything.call_count
            result2 = fetcher.fetch_news(["AAPL"], ["Apple Inc"])
            second_call_count = mock_client.get_everything.call_count

        # Second call should not have added more NewsAPI calls (cache hit)
        assert second_call_count == first_call_count, \
            "NewsAPI should not be called again on cache hit"
        assert result1 == result2

    def test_fetch_news_tab_failure_returns_empty_list(self, db_path):
        """
        If a NewsAPI call raises for one tab, that tab gets [] and others continue.
        """
        from backend.core.data_fetcher import DataFetcher

        call_count = 0

        def side_effect_fn(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("API quota exceeded")
            return _mock_newsapi_response()

        mock_client = MagicMock()
        mock_client.get_everything.side_effect = side_effect_fn

        with patch("backend.core.data_fetcher.settings") as mock_settings, \
             patch("backend.core.data_fetcher.NewsApiClient", return_value=mock_client):
            mock_settings.NEWSAPI_KEY = "test_key_123"
            fetcher = DataFetcher(db_path)
            result = fetcher.fetch_news(["AAPL"], ["Apple Inc"])

        # Should not raise
        assert set(result.keys()) == {"holdings", "india", "germany", "us"}
        # First tab (holdings) should be empty due to exception
        assert result["holdings"] == []
        # Other tabs should have articles
        assert len(result["india"]) >= 1

    def test_fetch_news_inserts_to_cache_table(self, db_path):
        """
        After fetch_news, news_cache table should have rows for the queries.
        """
        from backend.core.data_fetcher import DataFetcher

        mock_client = MagicMock()
        mock_client.get_everything.return_value = _mock_newsapi_response()

        with patch("backend.core.data_fetcher.settings") as mock_settings, \
             patch("backend.core.data_fetcher.NewsApiClient", return_value=mock_client):
            mock_settings.NEWSAPI_KEY = "test_key_123"
            fetcher = DataFetcher(db_path)
            fetcher.fetch_news(["AAPL"], ["Apple Inc"])

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_cache WHERE date = ?", (date.today().isoformat(),))
        count = cursor.fetchone()[0]
        conn.close()

        assert count >= 4, f"Expected >= 4 rows in news_cache, got {count}"


class TestBriefingPipeline:
    """Tests for extended BriefingOrchestrator.generate() with signals + news steps."""

    def _mock_portfolio(self):
        return {
            "holdings": [
                {
                    "ticker": "RELIANCE.NS",
                    "name": "Reliance Industries",
                    "quantity": 10,
                    "avg_buy": 2500.0,
                    "pl": 500.0,
                    "pl_pct": 2.0,
                    "currency": "INR",
                    "broker": "zerodha",
                }
            ],
            "total_inr": 500.0,
            "total_eur": 0.0,
            "cash_by_broker": {"zerodha": 0.0},
        }

    def test_generate_includes_news_key(self, db_path):
        """
        BriefingOrchestrator.generate() returns dict with top-level 'news' key
        containing sub-keys: holdings, india, germany, us.
        """
        from backend.core.briefing import BriefingOrchestrator

        mock_news = {"holdings": [], "india": [], "germany": [], "us": []}
        mock_signals = {"RELIANCE.NS": {"rsi_14": 55.0, "macd": 0.1, "macd_signal": 0.09,
                                         "macd_histogram": 0.01, "sma_50": 2400.0, "sma_200": None}}

        with patch("backend.core.briefing.DataFetcher") as MockDF, \
             patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

            MockDF.return_value.fetch_fx_rate.return_value = {
                "pair": "EURINR", "rate": 98.0, "low": 97.0, "high": 99.0,
                "timestamp": "2026-05-16T00:00:00+00:00",
            }
            MockDF.return_value.fetch_indices.return_value = {}
            MockDF.return_value.fetch_holding_prices.return_value = {}
            MockDF.return_value.fetch_signals.return_value = mock_signals
            MockDF.return_value.fetch_news.return_value = mock_news
            mock_portfolio.return_value = self._mock_portfolio()

            orchestrator = BriefingOrchestrator(db_path)
            result = orchestrator.generate()

        assert "news" in result, "generate() result must have 'news' key"
        assert set(result["news"].keys()) == {"holdings", "india", "germany", "us"}

    def test_generate_merges_signals_into_holdings(self, db_path):
        """
        After generate(), each holding in portfolio has rsi_14, macd, sma_50, sma_200 fields.
        """
        from backend.core.briefing import BriefingOrchestrator

        mock_news = {"holdings": [], "india": [], "germany": [], "us": []}
        mock_signals = {
            "RELIANCE.NS": {
                "rsi_14": 55.0, "macd": 0.1, "macd_signal": 0.09,
                "macd_histogram": 0.01, "sma_50": 2400.0, "sma_200": None,
            }
        }

        with patch("backend.core.briefing.DataFetcher") as MockDF, \
             patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

            MockDF.return_value.fetch_fx_rate.return_value = {
                "pair": "EURINR", "rate": 98.0, "low": 97.0, "high": 99.0,
                "timestamp": "2026-05-16T00:00:00+00:00",
            }
            MockDF.return_value.fetch_indices.return_value = {}
            MockDF.return_value.fetch_holding_prices.return_value = {}
            MockDF.return_value.fetch_signals.return_value = mock_signals
            MockDF.return_value.fetch_news.return_value = mock_news
            mock_portfolio.return_value = self._mock_portfolio()

            orchestrator = BriefingOrchestrator(db_path)
            result = orchestrator.generate()

        holdings = result.get("portfolio", {}).get("holdings", [])
        assert len(holdings) >= 1, "Expected at least one holding"
        h = holdings[0]
        assert "rsi_14" in h, "Holding should have rsi_14 after signal merge"
        assert h["rsi_14"] == 55.0, "rsi_14 value should match mock signals"
        assert "sma_200" in h, "Holding should have sma_200 after signal merge"
        assert h["sma_200"] is None, "sma_200 should be None per mock"

    def test_generate_signals_failure_does_not_crash(self, db_path):
        """
        If fetch_signals raises, generate() still returns a briefing (fail-open).
        """
        from backend.core.briefing import BriefingOrchestrator

        with patch("backend.core.briefing.DataFetcher") as MockDF, \
             patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

            MockDF.return_value.fetch_fx_rate.return_value = {
                "pair": "EURINR", "rate": 98.0, "low": 97.0, "high": 99.0,
                "timestamp": "2026-05-16T00:00:00+00:00",
            }
            MockDF.return_value.fetch_indices.return_value = {}
            MockDF.return_value.fetch_holding_prices.return_value = {}
            MockDF.return_value.fetch_signals.side_effect = Exception("signals failed")
            MockDF.return_value.fetch_news.return_value = {"holdings": [], "india": [], "germany": [], "us": []}
            mock_portfolio.return_value = self._mock_portfolio()

            orchestrator = BriefingOrchestrator(db_path)
            result = orchestrator.generate()

        assert "portfolio" in result, "generate() should still return portfolio on signals failure"
        assert "news" in result, "generate() should still return news on signals failure"

    def test_generate_news_failure_does_not_crash(self, db_path):
        """
        If fetch_news raises, generate() still returns a briefing with empty news dict (fail-open).
        """
        from backend.core.briefing import BriefingOrchestrator

        with patch("backend.core.briefing.DataFetcher") as MockDF, \
             patch("backend.core.briefing.get_portfolio_with_pl") as mock_portfolio:

            MockDF.return_value.fetch_fx_rate.return_value = {
                "pair": "EURINR", "rate": 98.0, "low": 97.0, "high": 99.0,
                "timestamp": "2026-05-16T00:00:00+00:00",
            }
            MockDF.return_value.fetch_indices.return_value = {}
            MockDF.return_value.fetch_holding_prices.return_value = {}
            MockDF.return_value.fetch_signals.return_value = {}
            MockDF.return_value.fetch_news.side_effect = Exception("news failed")
            mock_portfolio.return_value = self._mock_portfolio()

            orchestrator = BriefingOrchestrator(db_path)
            result = orchestrator.generate()

        assert "news" in result, "generate() should include 'news' key even on failure"
        assert set(result["news"].keys()) == {"holdings", "india", "germany", "us"}
