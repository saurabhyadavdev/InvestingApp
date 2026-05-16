---
phase: 02-intelligence-chat
plan: 01
subsystem: database
tags: [ta, newsapi, finnhub, anthropic, sqlite, pydantic, requirements]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: backend/requirements.txt, backend/database.py, backend/models.py established in Phase 1

provides:
  - ta>=0.11.0 replaces pandas-ta as technical indicators library
  - newsapi-python, finnhub-python, anthropic installed and importable
  - news_cache and analyst_cache SQLite tables via create_schema()
  - HoldingResponse extended with 11 Optional Phase 2 fields (rec, rsi_14, macd, macd_signal, macd_histogram, sma_50, sma_200, analyst_rating, analyst_target, analyst_num, ai_narrative)
  - BriefingResponse extended with news: Optional[dict] = None
  - ChatRequest and ChatResponse Pydantic models

affects:
  - 02-02 (signals engine — uses rec, rsi_14, macd fields and ta library)
  - 02-03 (news + analyst — uses news_cache, analyst_cache tables, newsapi-python, finnhub-python)
  - 02-04 (AI synthesis — uses anthropic, ai_narrative field, ChatRequest/ChatResponse)

# Tech tracking
tech-stack:
  added:
    - ta>=0.11.0 (pure-Python technical indicators; replaces pandas-ta)
    - newsapi-python>=0.2.7 (news fetching via NewsAPI)
    - finnhub-python>=2.4.28 (analyst ratings and price targets)
    - anthropic>=0.102.0 (Claude API for AI synthesis)
  patterns:
    - Optional fields with None defaults for backward-compatible Pydantic model extension
    - CREATE TABLE IF NOT EXISTS pattern for idempotent schema migrations

key-files:
  created: []
  modified:
    - backend/requirements.txt
    - backend/database.py
    - backend/models.py

key-decisions:
  - "Replace pandas-ta with ta library — pandas-ta has no Python 3.9 compatible release on PyPI (confirmed in RESEARCH.md)"
  - "All 11 new HoldingResponse fields are Optional[T] = None — preserves backward-compat with Phase 1 API consumers"
  - "news_cache uses UNIQUE(query, date) and analyst_cache uses UNIQUE(symbol, date) — idempotent upsert-ready"

patterns-established:
  - "Pattern: Extend Pydantic models with Optional fields (default None) to avoid breaking existing serialization"
  - "Pattern: Use CREATE TABLE IF NOT EXISTS for additive schema migrations — safe to call on every startup"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-05-16
---

# Phase 02 Plan 01: Phase 2 Dependency Scaffold Summary

**Replaced pandas-ta with ta library, installed four Phase 2 libs (newsapi-python, finnhub-python, anthropic), added news_cache and analyst_cache SQLite tables, and extended HoldingResponse with 11 Optional signal/analyst/AI fields plus ChatRequest/ChatResponse models**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-16T11:38:07Z
- **Completed:** 2026-05-16T11:39:41Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Removed pandas-ta (Python 3.9 incompatible) and added ta>=0.11.0 as drop-in replacement for technical indicators
- Added news_cache and analyst_cache tables to SQLite schema — downstream plans 02-03 and 02-04 can write to these immediately
- Extended HoldingResponse with 11 new Optional fields and BriefingResponse with news field; added ChatRequest/ChatResponse models — downstream plans have full data contracts

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace pandas-ta with ta library and add Phase 2 dependencies** - `cb7e000` (feat)
2. **Task 2: Add news_cache and analyst_cache tables to SQLite schema** - `87a063e` (feat)
3. **Task 3: Extend Pydantic models with Phase 2 fields and chat models** - `53aae4b` (feat)

## Files Created/Modified
- `backend/requirements.txt` - Removed pandas-ta, added ta>=0.11.0, newsapi-python>=0.2.7, finnhub-python>=2.4.28, anthropic>=0.102.0
- `backend/database.py` - Added news_cache and analyst_cache CREATE TABLE IF NOT EXISTS blocks inside create_schema()
- `backend/models.py` - Extended HoldingResponse (11 fields), BriefingResponse (news field), added ChatRequest/ChatResponse

## Decisions Made
- Replace pandas-ta with ta library: pandas-ta has no Python 3.9 compatible release on PyPI (confirmed in 02-RESEARCH.md slopcheck audit). ta>=0.11.0 covers RSI, MACD, Bollinger Bands, SMA, EMA — all indicators used in Plan 02-02.
- All new model fields set Optional[T] = None to ensure Phase 1 API callers continue to work without changes.
- news_cache and analyst_cache placed after chat_history in create_schema(), before conn.commit(), following existing pattern.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test failures (23 errors) in test_api.py and test_scheduler.py referencing `BriefingOrchestrator` attribute missing from `backend.main` were present before this plan's execution (confirmed by reverting changes and re-running tests). These are out-of-scope for Plan 02-01. 25 tests continue to pass unchanged.

Logged to deferred-items.md for tracking.

## Known Stubs

None - this plan adds schema and data contract definitions only. No UI rendering or data flow wired yet; that is the responsibility of Plans 02-02 through 02-04.

## Threat Flags

None - no new network endpoints, auth paths, or file access patterns introduced. Schema additions are additive and covered by T-02-02 mitigation (CREATE TABLE IF NOT EXISTS).

## User Setup Required

None - no external service configuration required at this stage. API keys for NewsAPI, Finnhub, and Anthropic will be configured in Plans 02-02 through 02-04.

## Next Phase Readiness
- Plan 02-02 (signals engine) can now import `ta` and write to `technical_indicators` table; `rec`, `rsi_14`, `macd`, `sma_50`, `sma_200` fields are ready in HoldingResponse
- Plan 02-03 (news + analyst) can import `newsapi` and `finnhub`; `news_cache` and `analyst_cache` tables exist; `analyst_rating`, `analyst_target`, `analyst_num` fields are ready
- Plan 02-04 (AI synthesis) can import `anthropic`; `ai_narrative` field and `ChatRequest`/`ChatResponse` models are ready; `news` field on BriefingResponse is ready

---
*Phase: 02-intelligence-chat*
*Completed: 2026-05-16*
