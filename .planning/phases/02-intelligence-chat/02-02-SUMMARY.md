---
phase: 02-intelligence-chat
plan: "02"
subsystem: api
tags: [yfinance, ta, newsapi, sqlite, technical-indicators, rsi, macd, sma, news-cache]

requires:
  - phase: 02-01
    provides: ta and newsapi-python installed; news_cache and technical_indicators tables in schema

provides:
  - DataFetcher.fetch_signals(tickers) — RSI-14, MACD, SMA50, SMA200 from 6mo OHLCV cached to technical_indicators
  - DataFetcher.fetch_news(tickers, holding_names) — 4-tab news from NewsAPI cached to news_cache
  - BriefingOrchestrator.generate() steps 4 and 5 — signals merged into holdings, news dict in briefing snapshot
  - GET /api/briefing response now contains briefing.news and briefing.portfolio.holdings[*].rsi_14

affects: [02-03, 02-04]

tech-stack:
  added: [ta 0.10.x (RSI/MACD/SMA indicators), newsapi-python (NewsAPI client)]
  patterns:
    - "Batch yfinance download with MultiIndex column handling (single vs multi-ticker)"
    - "Fail-open step pattern in BriefingOrchestrator.generate() — each step wrapped in try/except"
    - "Date-keyed SQLite cache (INSERT OR REPLACE, UNIQUE constraint) for expensive API calls"
    - "Parameterized ? placeholders for all SQL — no f-string SQL"

key-files:
  created:
    - tests/test_signals.py
    - tests/test_news.py
  modified:
    - backend/core/data_fetcher.py
    - backend/core/briefing.py
    - backend/main.py
    - backend/api/indices.py
    - tests/test_scheduler.py

key-decisions:
  - "ta library (not pandas-ta) used for indicators — matches RESEARCH.md verified API"
  - "Module-level helpers _null_signals, _cache_signals, _format_time_ago added to data_fetcher.py to keep DataFetcher methods readable"
  - "news_cache uses query string as cache key (not ticker) — enables macro tab caching alongside holdings tab"
  - "BriefingOrchestrator.generate() holds_tickers extracted from portfolio_data (not re-queried from DB) to keep steps 4+5 stateless"

patterns-established:
  - "Signal computation: check len(close) thresholds before computing (15 for RSI, 26 for MACD, 50 for SMA50, 200 for SMA200)"
  - "NaN check via value != value (float NaN is not equal to itself) — avoids import of math.isnan"
  - "News query for holdings: top-3 holding names joined with OR"

requirements-completed: [SIG-01, MKT-04, MKT-05, MKT-06, MKT-07]

duration: 3min
completed: 2026-05-16
---

# Phase 2 Plan 02: Intelligence Backend Summary

**RSI-14, MACD, SMA50/200 signals via ta library and 4-tab NewsAPI news (holdings + India/Germany/US macro) wired into BriefingOrchestrator as steps 4 and 5, with date-keyed SQLite caching for both**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-16T09:23:06Z
- **Completed:** 2026-05-16T09:26:30Z
- **Tasks:** 2 (TDD: RED-GREEN per task)
- **Files modified:** 5 (+ 2 test files created)

## Accomplishments
- `DataFetcher.fetch_signals(tickers)` computes RSI-14, MACD, SMA50, SMA200 from 6mo OHLCV via `ta` library; gracefully returns all-None for tickers with insufficient history; caches results to `technical_indicators` table
- `DataFetcher.fetch_news(tickers, holding_names)` fetches up to 5 articles per tab (holdings, india, germany, us) from NewsAPI with date-keyed cache in `news_cache` table; returns empty tabs without crashing when API key is missing or calls fail
- `BriefingOrchestrator.generate()` extended with two new fail-open steps: signals merged into each holding dict, news dict added as top-level briefing key
- All 63 tests pass (up from 48 at phase start)

## Task Commits

1. **Task 1 RED: Add failing tests for fetch_signals** - `93c9fad` (test) — also fixed backend/main.py BriefingOrchestrator import and indices.py KeyError bug
2. **Task 1 GREEN: Implement fetch_signals()** - `32649c7` (feat)
3. **Task 2 RED: Add failing tests for fetch_news + briefing pipeline** - `453a0e1` (test)
4. **Task 2 GREEN: Extend briefing pipeline with steps 4+5** - `a02676e` (feat)

## Files Created/Modified
- `backend/core/data_fetcher.py` — Added `fetch_signals()`, `fetch_news()`, `_null_signals()`, `_cache_signals()`, `_format_time_ago()` helpers; imports `ta`, `newsapi`, `settings`, `json`, `timedelta`
- `backend/core/briefing.py` — Extended `generate()` with steps 4 (signals) and 5 (news); added `"news"` key to briefing assembly dict
- `backend/main.py` — Moved `BriefingOrchestrator` import to module level (was inside lifespan function) so conftest mock works
- `backend/api/indices.py` — Fixed KeyError bug in list comprehension when `^NDX` absent from fetch result
- `tests/test_signals.py` — 6 tests for fetch_signals (TDD RED/GREEN)
- `tests/test_news.py` — 9 tests: 5 for fetch_news, 4 for briefing pipeline news/signals steps
- `tests/test_scheduler.py` — Added fetch_signals/fetch_news mock return values to prevent JSON serialization errors

## Decisions Made
- Used module-level helpers (`_null_signals`, `_cache_signals`, `_format_time_ago`) outside the DataFetcher class to keep method code readable
- News query for holdings tab uses top 3 holding names joined with OR — simple and avoids per-holding API calls
- NaN detection uses `val != val` (float NaN property) rather than `math.isnan` to avoid extra import
- `holding_tickers` variable from Step 4 reused in Step 5 — avoids second DB query for ticker list

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed backend/main.py missing module-level BriefingOrchestrator import**
- **Found during:** Pre-task baseline test run
- **Issue:** conftest.py patches `backend.main.BriefingOrchestrator` but the class was only imported inside the `lifespan` async function, making it unavailable as a module attribute; 23 tests were erroring
- **Fix:** Added `from backend.core.briefing import BriefingOrchestrator` at module level in `main.py`; removed duplicate local import from lifespan
- **Files modified:** backend/main.py
- **Verification:** All 48 pre-existing tests passed after fix
- **Committed in:** 93c9fad (Task 1 RED commit)

**2. [Rule 1 - Bug] Fixed KeyError in indices.py list comprehension**
- **Found during:** Pre-task baseline test run (after fix 1 unmasked it)
- **Issue:** `for v in [data[sym]]` evaluates `data[sym]` before `if sym in data` guard, causing KeyError for `^NDX` when mock data has only 4 symbols
- **Fix:** Rewrote comprehension as `if sym in data` guard + direct `data[sym]` dict access
- **Files modified:** backend/api/indices.py
- **Verification:** `test_get_indices_returns_four_indices` passes; all tests pass
- **Committed in:** 93c9fad (Task 1 RED commit)

**3. [Rule 1 - Bug] Fixed existing test_scheduler.py test broken by new steps**
- **Found during:** Task 2 GREEN verification
- **Issue:** `test_briefing_generate_creates_snapshot` mocked DataFetcher but didn't set `fetch_signals`/`fetch_news` return values; `MagicMock` objects are not JSON-serializable, causing briefing_snapshots INSERT to fail
- **Fix:** Added `MockDF.return_value.fetch_signals.return_value = {}` and `MockDF.return_value.fetch_news.return_value = {...}` in two tests
- **Files modified:** tests/test_scheduler.py
- **Verification:** All 63 tests pass
- **Committed in:** a02676e (Task 2 GREEN commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 3 blocker)
**Impact on plan:** All fixes necessary for a clean test baseline and correct briefing storage. No scope creep.

## Issues Encountered
None — all issues handled via deviation rules above.

## Known Stubs
None — both methods return real data (or empty lists on failure). No hardcoded placeholder values.

## Threat Flags
None — no new network endpoints, auth paths, or schema changes introduced beyond what was planned. NEWSAPI_KEY read from env via settings (T-02-04 already mitigated). All SQL parameterized (T-02-05 already mitigated).

## Next Phase Readiness
- Plan 02-03 (frontend signals + news UI) can now consume `briefing.portfolio.holdings[*].rsi_14` and `briefing.news` from GET /api/briefing
- Plan 02-04 (AI synthesis) has signal data available to include in Claude prompt context
- Ready for Plan 02-03

---
*Phase: 02-intelligence-chat*
*Completed: 2026-05-16*
