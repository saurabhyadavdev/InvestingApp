"""
POST /api/chat — stateless chat endpoint backed by Groq (llama-3.3-70b, free tier).

Security notes:
  - Anti-hallucination system prompt: "Answer using ONLY the data in the briefing below."
  - compact_briefing strips raw news article bodies to keep prompt under ~4000 tokens.
  - GROQ_API_KEY never appears in briefing JSON or API responses.
  - Returns ChatResponse on all error paths — never raises HTTP 500.
"""
import json
import logging

from fastapi import APIRouter
from groq import Groq

from backend.models import ChatRequest, ChatResponse
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    if not settings.GROQ_API_KEY:
        return ChatResponse(response="Chat unavailable — set GROQ_API_KEY in .env")

    try:
        compact_briefing = {
            "holdings": [
                {
                    "ticker": h.get("ticker"),
                    "name": h.get("name"),
                    "rec": h.get("rec"),
                    "rsi_14": h.get("rsi_14"),
                    "ai_narrative": h.get("ai_narrative"),
                    "pl_pct": h.get("pl_pct"),
                    "day_change_pct": h.get("day_change_pct"),
                    "current_price": h.get("current_price"),
                    "analyst_rating": h.get("analyst_rating"),
                    "analyst_target": h.get("analyst_target"),
                }
                for h in req.briefing.get("portfolio", {}).get("holdings", [])
            ],
            "indices": req.briefing.get("indices", {}),
            "fx": {
                k: v
                for k, v in req.briefing.get("fx", {}).items()
                if k in ("rate", "timestamp")
            },
            # News headlines (title + source only — no full bodies to stay under token limit)
            "news": {
                tab: [
                    {
                        "title": a.get("title"),
                        "source": a.get("source"),
                        "publishedAt": a.get("publishedAt"),
                    }
                    for a in (articles[:6] if isinstance(articles, list) else [])
                ]
                for tab, articles in req.briefing.get("news", {}).items()
            },
        }

        system_prompt = (
            "You are a personal investing analyst assistant. Use the user's portfolio briefing "
            "data below as your primary context, but you may also draw on your general financial "
            "knowledge to answer questions about market events, stock movements, economic factors, "
            "and investment concepts. When the briefing contains relevant data (prices, signals, "
            "analyst ratings, news headlines), reference it specifically. For questions about "
            "broader market context or reasons behind price movements, use your knowledge to "
            "provide helpful analysis.\n\n"
            "Today's briefing data:\n" + json.dumps(compact_briefing, default=str)
        )

        client = Groq(api_key=settings.GROQ_API_KEY)
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message},
            ],
            max_tokens=512,
        )
        return ChatResponse(response=message.choices[0].message.content)

    except Exception as exc:
        logger.error("POST /api/chat failed: %s", exc)
        return ChatResponse(response=f"Chat unavailable: {exc}")
