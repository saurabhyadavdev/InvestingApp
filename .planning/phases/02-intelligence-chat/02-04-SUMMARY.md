---
phase: 02-intelligence-chat
plan: 04
subsystem: api, ai, ui
tags: [anthropic, claude-haiku, finnhub, react, chat, ai-synthesis, analyst-ratings]

# Dependency graph
requires:
  - phase: 02-intelligence-chat
    provides: signals (pandas-ta), news (NewsAPI), portfolio P&L, briefing pipeline steps 1-5
  - phase: 02-intelligence-chat
    plan: 02-01
    provides: ChatRequest + ChatResponse Pydantic models in models.py
provides:
  - fetch_analyst() on DataFetcher — Finnhub consensus ratings + price targets cached to analyst_cache
  - ai_synthesis.py — rec_from_signals (rule-based), synthesise_holding (Claude Haiku 4.5 JSON), synthesise_holdings (orchestrator)
  - briefing pipeline steps 6 (analyst) + 7 (AI synthesis) — each holding now has rec + ai_narrative
  - POST /api/chat — stateless chat endpoint with anti-hallucination system prompt
  - ChatPanel.jsx — fixed bottom chat UI with collapse/expand, message history, loading dots
  - sendChat() in api.js — frontend API call to POST /api/chat
affects:
  - Phase 2 UAT: full intelligence layer (signals + analyst + AI synthesis + chat) is now operational end-to-end

# Tech tracking
tech-stack:
  added:
    - finnhub (Python SDK, analyst ratings + price targets)
    - anthropic (Python SDK, Claude Haiku 4.5 for synthesis + chat)
  patterns:
    - Two-stage recommendation: rule-based votes (rec_from_signals) → Claude Haiku 4.5 confirmation/override
    - Anti-hallucination: "Based ONLY on the data below" system prompt (D-08); user message in messages[] role, not system prompt
    - Compact briefing injection: strip news bodies before injecting into system prompt (T-02-15, ~4000 token budget)
    - Regex fallback for malformed Claude JSON responses (T-02-18)
    - Cash deployment context injected when any broker balance > 1000 (FX-04)

key-files:
  created:
    - backend/core/ai_synthesis.py — rec_from_signals, synthesise_holding, synthesise_holdings
    - backend/api/chat.py — POST /api/chat router
    - frontend/src/components/ChatPanel.jsx — full chat UI component
    - tests/test_ai_synthesis.py — 7 unit tests for ai_synthesis module
  modified:
    - backend/core/data_fetcher.py — added fetch_analyst(), finnhub import
    - backend/core/briefing.py — steps 6+7 added to pipeline, import synthesise_holdings
    - backend/main.py — chat_router registered
    - frontend/src/api.js — sendChat() export added
    - frontend/src/Dashboard.jsx — ChatPanel replaces placeholder div
    - frontend/src/index.css — .typing-dots animation CSS added
    - tests/test_api.py — 2 chat endpoint tests added
    - tests/test_scheduler.py — fetch_analyst mock added to prevent MagicMock JSON error

key-decisions:
  - "Rule-based rec_from_signals used as both fallback (no API key) and pre-Claude signal — buy_votes/sell_votes weighted by RSI extremes, MACD direction, and analyst consensus"
  - "Claude response parsed with json.loads() first; regex {.*?} fallback if that fails; rule-based rec as ultimate fallback (T-02-18 mitigated)"
  - "compact_briefing strips news bodies before injecting into POST /api/chat system prompt to stay under ~4000 token budget"
  - "fetch_analyst keyed by original yfinance ticker (not Finnhub format) for consistency with rest of pipeline"
  - "test_scheduler.py tests updated to mock fetch_analyst return value — necessary after adding step 6 to pipeline"

patterns-established:
  - "Graceful degradation: empty FINNHUB_KEY → fetch_analyst returns {}; empty ANTHROPIC_API_KEY → rule-based rec + fixed narrative"
  - "Per-ticker try/except in fetch_analyst: single Finnhub failure never aborts the whole batch"
  - "Chat endpoint never raises HTTP 500 — all exception paths return ChatResponse(response=f'Chat unavailable: {exc}')"

requirements-completed:
  - SIG-02
  - SIG-03
  - SIG-04
  - BRIEF-04
  - BRIEF-05
  - FX-04

# Metrics
duration: 25min
completed: 2026-05-16
---

# Phase 2 Plan 04: Intelligence Layer (Analyst + AI + Chat) Summary

**Finnhub analyst ratings + Claude Haiku 4.5 per-holding BUY/HOLD/SELL synthesis + POST /api/chat with anti-hallucination prompt + React ChatPanel fixed-bottom UI**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-16T10:00:00Z
- **Completed:** 2026-05-16T10:25:00Z
- **Tasks:** 3 (Tasks 1-3 complete; Task 4 checkpoint awaiting human verification)
- **Files modified:** 12

## Accomplishments

- fetch_analyst() method added to DataFetcher: translates yfinance tickers to Finnhub format, fetches consensus ratings and price targets, caches to analyst_cache with parameterized SQL
- ai_synthesis.py module created with three public functions: rec_from_signals (weighted vote system), synthesise_holding (Claude Haiku 4.5 JSON output), synthesise_holdings (batch orchestrator with cash deployment context)
- Briefing pipeline extended to 10 steps: analyst fetch (step 6) and AI synthesis (step 7) now enrich every holding with rec + ai_narrative before snapshot assembly
- POST /api/chat endpoint: stateless, compact-briefing injection, anti-hallucination system prompt, max_tokens=512, graceful error returns
- ChatPanel React component: fixed bottom bar (44px collapsed, 300px expanded), animated typing dots, keyboard submit, auto-scroll, error bubble

## Task Commits

1. **Tasks 1-3: analyst fetch + AI synthesis + briefing pipeline + chat endpoint + ChatPanel** - `7cc6d7e` (feat)

**Plan metadata:** pending (created with this SUMMARY)

## Files Created/Modified

- `backend/core/ai_synthesis.py` — rec_from_signals, synthesise_holding, synthesise_holdings
- `backend/api/chat.py` — POST /api/chat router with anti-hallucination prompt
- `frontend/src/components/ChatPanel.jsx` — fixed bottom chat panel component
- `tests/test_ai_synthesis.py` — 7 unit tests (all passing)
- `backend/core/data_fetcher.py` — fetch_analyst() method added, finnhub imported
- `backend/core/briefing.py` — steps 6+7 added to pipeline
- `backend/main.py` — chat_router registered
- `frontend/src/api.js` — sendChat() exported
- `frontend/src/Dashboard.jsx` — ChatPanel replaces placeholder div
- `frontend/src/index.css` — .typing-dots + @keyframes blink added
- `tests/test_api.py` — 2 chat endpoint tests added
- `tests/test_scheduler.py` — fetch_analyst mock added

## Decisions Made

- Two-stage recommendation: rule-based votes computed first, then Claude asked to confirm or override. Rule-based also used as fallback when ANTHROPIC_API_KEY absent.
- `compact_briefing` (holdings summary + indices + fx rate, no news bodies) injected as system context to stay under ~4000 tokens per chat turn (T-02-15).
- fetch_analyst keys results by original yfinance ticker format, not translated Finnhub format, for consistency with the rest of the pipeline.
- test_scheduler.py needed MockDF.return_value.fetch_analyst.return_value = {} added — without it the mock returns MagicMock objects that break JSON serialization in the briefing store step.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_scheduler.py tests broken by new fetch_analyst pipeline step**
- **Found during:** Task 1 (after implementing steps 6+7 in briefing.py)
- **Issue:** `test_briefing_generate_creates_snapshot` and `test_startup_generates_briefing_if_missing` mock DataFetcher but did not set `fetch_analyst` return value. When `synthesise_holdings` received MagicMock values for analyst data, holdings ended up with MagicMock objects in analyst_* fields, causing `json.dumps()` to fail with "Object of type MagicMock is not JSON serializable" — briefing snapshot not stored.
- **Fix:** Added `MockDF.return_value.fetch_analyst.return_value = {}` to both affected tests.
- **Files modified:** tests/test_scheduler.py
- **Verification:** `python3 -m pytest tests/ -x -q` → 72 passed.
- **Committed in:** 7cc6d7e (combined task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Fix required for test suite correctness after adding pipeline step. No scope creep.

## Issues Encountered

None beyond the test fixture mock gap documented above.

## User Setup Required

The following API keys must be set in `.env` before the full intelligence layer is functional:

| Key | Source | Required for |
|-----|--------|-------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ → API Keys | AI synthesis per holding + chat endpoint |
| `FINNHUB_KEY` | https://finnhub.io/ → Dashboard → API Key | Analyst ratings + price targets |
| `NEWS_API_KEY` | https://newsapi.org/ → Get API Key | News tabs (already required from Plan 03) |

**Graceful degradation without keys:**
- No `ANTHROPIC_API_KEY`: `ai_narrative = "AI synthesis unavailable — set ANTHROPIC_API_KEY in .env"`, rec = rule-based
- No `FINNHUB_KEY`: `analyst_rating = None`, displayed as "No analyst coverage" in UI
- No `NEWS_API_KEY`: all news tabs show empty state

## Next Phase Readiness

- Full Phase 2 intelligence layer is code-complete and test-passing
- Task 4 (checkpoint:human-verify) is pending — user must verify UI manually (see plan for verification steps)
- After human verification: Phase 2 is complete, ready for Phase 3

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes beyond what was planned in the threat model (T-02-12 through T-02-18). All mitigations applied as specified.

---
*Phase: 02-intelligence-chat*
*Completed: 2026-05-16*
