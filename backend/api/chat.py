"""
POST /api/chat — stateless chat endpoint backed by Claude Haiku 4.5.

Security notes (T-02-12, T-02-13, T-02-15):
  - Anti-hallucination system prompt: "Answer using ONLY the data in the briefing below."
  - User message goes in the `messages` array (user role), NOT in the system prompt.
  - compact_briefing strips raw news article bodies and API keys to keep system prompt
    under ~4000 tokens (T-02-15 max_tokens=512 mitigation).
  - ANTHROPIC_API_KEY never appears in briefing JSON or API responses.
  - Returns ChatResponse on all error paths — never raises HTTP 500.
"""
import json
import logging

from fastapi import APIRouter

import anthropic

from backend.models import ChatRequest, ChatResponse
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def post_chat(req: ChatRequest) -> ChatResponse:
    """
    Answer a user question about today's briefing using Claude Haiku 4.5.

    The briefing is injected as a compact system-prompt context (holdings summary,
    indices closes, FX rate only — news article bodies excluded to stay within token budget).

    Returns ChatResponse on all paths; never raises HTTP 500.
    """
    if not settings.ANTHROPIC_API_KEY:
        return ChatResponse(response="Chat unavailable — set ANTHROPIC_API_KEY in .env")

    try:
        # Build compact briefing — exclude raw news bodies to stay within ~4000 token budget
        # (T-02-15 mitigation). Include only: holding summary, indices, fx rate + timestamp.
        compact_briefing = {
            "holdings": [
                {
                    "ticker": h.get("ticker"),
                    "rec": h.get("rec"),
                    "rsi_14": h.get("rsi_14"),
                    "ai_narrative": h.get("ai_narrative"),
                    "pl_pct": h.get("pl_pct"),
                }
                for h in req.briefing.get("portfolio", {}).get("holdings", [])
            ],
            "indices": req.briefing.get("indices", {}),
            "fx": {
                k: v
                for k, v in req.briefing.get("fx", {}).items()
                if k in ("rate", "timestamp")
            },
        }

        # Anti-hallucination system prompt (D-08, T-02-12 mitigation)
        system_prompt = (
            "You are a personal investing analyst assistant. Answer the user's question using ONLY "
            "the data in the briefing below. Do not invent facts, prices, or recommendations not "
            "present in the data. If something is not in the data, say "
            "'I don't have that information in today's briefing'.\n\n"
            "Today's briefing data:\n" + json.dumps(compact_briefing, default=str)
        )

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
        return ChatResponse(response=message.content[0].text)

    except Exception as exc:
        logger.error("POST /api/chat failed: %s", exc)
        return ChatResponse(response=f"Chat unavailable: {exc}")
