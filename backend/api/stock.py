"""
GET /api/stock/{ticker}/detail — on-demand stock detail endpoint.

Returns live signals, analyst data, and structured AI narrative (three sections)
for a given ticker. All fields are nullable — never returns 500 for missing data.
"""
import logging

from fastapi import APIRouter

from backend.config import settings
from backend.core.data_fetcher import DataFetcher
from backend.core.ai_synthesis import rec_from_signals, synthesise_holding_ondemand
from groq import Groq
from backend.models import StockDetailResponse, StockDetailAI

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/stock/{ticker}/detail", response_model=StockDetailResponse)
async def get_stock_detail(ticker: str) -> StockDetailResponse:
    fetcher = DataFetcher(settings.DB_PATH)

    signals = fetcher.fetch_signals([ticker]).get(ticker, {})
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
