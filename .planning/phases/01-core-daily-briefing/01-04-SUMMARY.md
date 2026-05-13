---
phase: 01-core-daily-briefing
plan: 04
subsystem: briefing-orchestration
tags: [apscheduler, briefing, orchestrator, react, dashboard, tdd]
dependency_graph:
  requires:
    - 01-01-PLAN.md (walking skeleton — SQLite schema, FastAPI app, briefing_snapshots table)
    - 01-02-PLAN.md (portfolio import — get_portfolio_with_pl)
    - 01-03-PLAN.md (market data — DataFetcher.fetch_indices, fetch_fx_rate)
  provides:
    - BriefingOrchestrator.generate() aggregating portfolio + indices + FX into briefing_snapshots
    - APScheduler job "morning_briefing" at 07:00 IST (Asia/Kolkata)
    - GET /api/briefing returning latest cached briefing JSON
    - POST /api/refresh triggering on-demand briefing regeneration
    - React Dashboard with Morning Briefing heading, Refresh Now button, footer timestamp
    - fetchBriefing() + triggerRefresh() in api.js
  affects:
    - Phase 2 (intelligence layer reads briefing_snapshots for context)
tech_stack:
  added:
    - APScheduler CronTrigger with Asia/Kolkata timezone
    - zoneinfo.ZoneInfo for IST briefing_date calculation
  patterns:
    - TDD RED/GREEN for Task 1 (failing tests committed before implementation)
    - Fail-open exception handling in BriefingOrchestrator.generate() (T-04-04)
    - json.loads() only — never eval() (T-04-03 mitigation)
    - Parameterized ? SQL placeholders throughout
    - Startup auto-generate: briefing created on first launch if none cached
    - Optional[dict] instead of dict | None (Python 3.9 compat)
key_files:
  created:
    - backend/core/briefing.py
    - backend/scheduler.py
    - backend/api/briefing.py
    - backend/api/refresh.py
    - frontend/src/Dashboard.jsx
    - tests/test_scheduler.py
  modified:
    - backend/main.py (APScheduler wired; briefing + refresh routers added; startup auto-generate)
    - backend/models.py (added BriefingResponse + RefreshResponse)
    - frontend/src/App.jsx (simplified to single fetchBriefing(); renders Dashboard)
    - frontend/src/api.js (added fetchBriefing + triggerRefresh)
decisions:
  - "Optional[dict] instead of dict | None union — Python 3.9 does not support X | Y union syntax"
  - "Startup briefing auto-generate wrapped in try/except — data fetch failure must not block server startup"
  - "Test for 404 clears briefing_snapshots after test_client creation (startup lifespan inserts a row)"
metrics:
  duration: "~4 minutes"
  completed: "2026-05-13T19:09:00Z"
  tasks_completed: 2
  files_created: 6
  files_modified: 4
  tests_passing: 39
---

# Phase 01 Plan 04: Briefing Orchestration Summary

**One-liner:** BriefingOrchestrator aggregates portfolio + indices + FX into briefing_snapshots; APScheduler fires at 07:00 IST; GET /api/briefing + POST /api/refresh endpoints; React Dashboard with Morning Briefing heading, conditional Refresh Now button, and Last updated footer.

---

## What Was Built

Complete briefing orchestration and dashboard layer — the final piece of Phase 1 MVP:

- **backend/core/briefing.py** — `BriefingOrchestrator` class:
  - `generate()`: fetches FX → indices → portfolio with fail-open exception handling per section; assembles `{portfolio, indices, fx, generated_at, briefing_date}` dict; INSERTs into `briefing_snapshots` with parameterized `?` SQL (T-04-03). `generated_at` is UTC ISO 8601 with `Z` suffix; `briefing_date` is IST YYYY-MM-DD.
  - `get_latest()`: queries `briefing_snapshots ORDER BY created_at DESC LIMIT 1`; deserializes with `json.loads()` (never `eval()`).

- **backend/scheduler.py** — `init_scheduler(scheduler, db_path)`: registers `_run_morning_briefing` job with `CronTrigger(hour=7, minute=0, second=0, timezone="Asia/Kolkata")`, `id="morning_briefing"`. The wrapper catches all exceptions from `generate()` and logs them without re-raising (T-04-04 mitigation).

- **backend/api/briefing.py** — `GET /api/briefing`: returns `get_latest()` result with `fetched_at` timestamp appended; raises `HTTPException(404, "No briefing generated yet")` if table is empty.

- **backend/api/refresh.py** — `POST /api/refresh`: calls `generate()` and returns `{"status": "Briefing refreshed", "generated_at": str}`.

- **backend/main.py** — Updated: replaces APScheduler stub with `init_scheduler(scheduler, db_path)` call; starts scheduler on startup; includes `briefing_router` + `refresh_router`; auto-generates initial briefing if `briefing_snapshots` is empty on startup (non-fatal try/except).

- **backend/models.py** — Added `BriefingResponse` (portfolio, indices, fx, generated_at, briefing_date, fetched_at) and `RefreshResponse` (status, generated_at).

- **frontend/src/Dashboard.jsx** — Unified briefing display:
  - Header: `Morning Briefing` (h1, 28px semibold), date subtitle, conditional `Refresh Now` button (shown if hour >= 12 or data > 6h stale)
  - Sections: ImportCSV → Your Portfolio (PortfolioTable) → AllocationCard → Market Indices (IndicesCard) → EUR/INR Rate (FXCard)
  - Footer: "Last updated: {HH:MM} IST, YYYY-MM-DD" with Feather clock SVG icon (aria-label="Last updated")
  - Error state: "Market data unavailable — {time}. Last updated: unknown. Retry in 1 minute."
  - Loading state: "Loading briefing..."

- **frontend/src/App.jsx** — Simplified: single `fetchBriefing()` on mount; stores in `briefing` state; renders `<Dashboard briefing={briefing} loading={loading} onRefresh={loadBriefing} />`.

- **frontend/src/api.js** — Added `fetchBriefing()` (GET /api/briefing) and `triggerRefresh()` (POST /api/refresh).

- **tests/test_scheduler.py** — 7 new tests:
  - `test_briefing_generate_creates_snapshot` — generate() with mocked DataFetcher + portfolio returns required keys + inserts 1 DB row
  - `test_get_latest_returns_none_when_empty` — get_latest() returns None on empty DB
  - `test_get_briefing_endpoint_no_data` — GET /api/briefing returns 404 with exact "No briefing generated yet"
  - `test_get_briefing_endpoint_returns_latest` — GET /api/briefing returns 200 with briefing keys after seeding DB
  - `test_refresh_endpoint_triggers_generation` — POST /api/refresh returns 200 with `status="Briefing refreshed"`
  - `test_morning_briefing_job_registered` — init_scheduler registers job at hour=7 with Asia/Kolkata timezone
  - `test_startup_generates_briefing_if_missing` — fetch_indices called when briefing_snapshots is empty

---

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for BriefingOrchestrator + scheduler + API | 1c32a33 | tests/test_scheduler.py |
| 1 (GREEN) | BriefingOrchestrator + scheduler + briefing/refresh endpoints | fbd9614 | backend/core/briefing.py, backend/scheduler.py, backend/api/briefing.py, backend/api/refresh.py, backend/main.py, backend/models.py, tests/test_scheduler.py |
| 2 | React Dashboard — unified briefing view + Header + Footer | 5b168a6 | frontend/src/Dashboard.jsx, frontend/src/App.jsx, frontend/src/api.js |

---

## Verification

All acceptance criteria met:

- `backend/core/briefing.py` contains "briefing_snapshots" and "generated_at" — VERIFIED
- `backend/scheduler.py` contains "morning_briefing" (job id) — VERIFIED
- `backend/scheduler.py` contains "Asia/Kolkata" — VERIFIED
- `backend/scheduler.py` contains `CronTrigger(hour=7` — VERIFIED
- `backend/api/briefing.py` contains "No briefing generated yet" (exact) — VERIFIED
- `backend/api/refresh.py` contains "Briefing refreshed" (exact) — VERIFIED
- `backend/main.py` includes both briefing and refresh routers — VERIFIED
- All 7 new pytest tests pass (39 total) — VERIFIED
- `backend/core/briefing.py` uses "?" placeholder in sqlite3 execute (no f-string SQL) — VERIFIED
- `frontend/src/Dashboard.jsx` contains "Morning Briefing" (h1) — VERIFIED
- `frontend/src/Dashboard.jsx` contains "Refresh Now" (conditional button) — VERIFIED
- `frontend/src/Dashboard.jsx` contains "Last updated" (footer) — VERIFIED
- `frontend/src/Dashboard.jsx` contains "Your Portfolio" and "Market Indices" and "EUR/INR Rate" — VERIFIED
- `frontend/src/Dashboard.jsx` contains "Market data unavailable" (error state) — VERIFIED
- `frontend/src/api.js` contains `fetch('/api/briefing')` and `fetch('/api/refresh'` — VERIFIED
- `npm run build` exits 0 (207KB bundle) — VERIFIED

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Python 3.9 incompatible union type syntax in briefing.py**
- **Found during:** Task 1 GREEN phase (TypeError at module import)
- **Issue:** `dict | None` union syntax for `get_latest()` return type annotation; Python 3.9 doesn't support `X | Y` union syntax (requires Python 3.10+)
- **Fix:** Changed to `Optional[dict]` with `from typing import Optional` import
- **Files modified:** backend/core/briefing.py
- **Commit:** fbd9614

**2. [Rule 1 - Bug] Fixed test_get_briefing_endpoint_no_data test — startup lifespan conflict**
- **Found during:** Task 1 GREEN phase (test expected 404 but got 200)
- **Issue:** The `test_client` fixture triggers FastAPI lifespan which includes startup auto-generate; this inserts a row into `briefing_snapshots` before the test body runs, making 404 unreachable
- **Fix:** Test clears `briefing_snapshots` table after test_client is created, before making the request
- **Files modified:** tests/test_scheduler.py
- **Commit:** fbd9614

---

## Known Stubs

None. All endpoints return real data:
- GET /api/briefing serves data aggregated from real yfinance + portfolio calculations
- Dashboard renders all sections with real data from the briefing endpoint
- "Refresh Now" button visibility is driven by real timestamps (not hardcoded)

---

## Threat Surface Scan

All mitigations from the plan's `<threat_model>` are implemented:

| Threat | Mitigation Status |
|--------|-------------------|
| T-04-01 POST /api/refresh DoS | Accepted — local single-user app; no rate limiting in Phase 1 |
| T-04-02 briefing_snapshots disclosure | Accepted — local data; no external exposure |
| T-04-03 briefing_json deserialization | json.loads() only in get_latest() — never eval() — VERIFIED |
| T-04-04 APScheduler job exception | _run_morning_briefing() wraps generate() in try/except; logs without re-raising — VERIFIED |
| T-04-05 POST /api/refresh response injection | Response returns hardcoded "Briefing refreshed" string — VERIFIED |

No new threat surface introduced beyond what the plan modeled.

---

## TDD Gate Compliance

| Gate | Status |
|------|--------|
| Task 1 RED (test commit) | 1c32a33 — `test(01-04): add failing tests for BriefingOrchestrator, scheduler, briefing/refresh endpoints (RED)` |
| Task 1 GREEN (feat commit) | fbd9614 — `feat(01-04): implement BriefingOrchestrator, APScheduler 07:00 IST, briefing + refresh endpoints` |

RED/GREEN gate sequence present in git log. TDD compliance: PASSED.

---

## Self-Check: PASSED

- backend/core/briefing.py — FOUND
- backend/scheduler.py — FOUND
- backend/api/briefing.py — FOUND
- backend/api/refresh.py — FOUND
- backend/main.py — FOUND (updated)
- backend/models.py — FOUND (updated)
- frontend/src/Dashboard.jsx — FOUND
- frontend/src/App.jsx — FOUND (updated)
- frontend/src/api.js — FOUND (updated)
- tests/test_scheduler.py — FOUND
- Commit 1c32a33 (Task 1 RED) — FOUND
- Commit fbd9614 (Task 1 GREEN) — FOUND
- Commit 5b168a6 (Task 2) — FOUND
- 39/39 pytest tests passing — VERIFIED
- npm run build exits 0 — VERIFIED
