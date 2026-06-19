"""
GET /api/stock/{ticker}/detail — on-demand stock detail endpoint.
GET /api/stock/search?q=<query> — search stocks by name or ticker via yfinance.

Returns live signals, analyst data, and structured AI narrative (three sections)
for a given ticker. All fields are nullable — never returns 500 for missing data.
"""
import logging

from fastapi import APIRouter, Query
import yfinance as yf

from backend.config import settings
from backend.core.data_fetcher import DataFetcher
from backend.core.ai_synthesis import rec_from_signals, synthesise_holding_ondemand
from groq import Groq
from backend.models import StockDetailResponse, StockDetailAI

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/stock/search")
async def search_stocks(q: str = Query(..., min_length=1, max_length=100)) -> list[dict]:
    """Return up to 12 matching stocks for a name/ticker query."""
    try:
        results = yf.Search(q, max_results=12).quotes
        return [
            {
                "symbol": r.get("symbol", ""),
                "name": r.get("shortname") or r.get("longname") or "",
                "exchange": r.get("exchange") or r.get("fullExchangeName") or "",
            }
            for r in results
            if r.get("symbol")
        ]
    except Exception as exc:
        logger.warning("Stock search failed for %r: %s", q, exc)
        return []


def _fetch_price_data(ticker: str) -> dict:
    """Fetch current price and daily change % for a single ticker via yfinance Ticker.history."""
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or hist.empty:
            return {}
        closes = hist["Close"].dropna()
        if len(closes) < 1:
            return {}
        current_price = round(float(closes.iloc[-1]), 4)
        day_change_pct = None
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            if prev > 0:
                day_change_pct = round((current_price - prev) / prev * 100, 2)
        return {"current_price": current_price, "day_change_pct": day_change_pct}
    except Exception as exc:
        logger.warning("_fetch_price_data failed for %s: %s", ticker, exc)
        return {}


@router.get("/stock/{ticker}/detail", response_model=StockDetailResponse)
async def get_stock_detail(ticker: str) -> StockDetailResponse:
    fetcher = DataFetcher(settings.DB_PATH)

    signals = fetcher.fetch_signals([ticker]).get(ticker, {})
    signals.update(_fetch_price_data(ticker))
    analyst = fetcher.fetch_analyst([ticker]).get(ticker, {})

    try:
        news_headlines = fetcher.fetch_news([ticker], [ticker]).get("holdings", [])[:3]
    except Exception as exc:
        logger.warning("fetch_news failed for %s: %s", ticker, exc)
        news_headlines = []

    rec = rec_from_signals(signals, analyst)

    ai = StockDetailAI()
    if settings.GROQ_API_KEY:
        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            ai_dict = synthesise_holding_ondemand(client, ticker, signals, analyst, news_headlines)
            ai = StockDetailAI(
                today_move=ai_dict.get("today_move"),
                recommendation=ai_dict.get("recommendation"),
                outlook=ai_dict.get("outlook"),
            )
        except Exception as exc:
            logger.warning("AI synthesis failed for %s: %s", ticker, exc)
            ai = StockDetailAI()

    return StockDetailResponse(
        ticker=ticker,
        signals=signals or None,
        analyst=analyst or None,
        ai=ai,
        rec=rec,
    )
