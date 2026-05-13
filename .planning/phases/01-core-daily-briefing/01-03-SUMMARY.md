---
phase: 01-core-daily-briefing
plan: 03
subsystem: market-data
tags: [yfinance, indices, fx, timezone, sqlite, fastapi, react, tdd]
dependency_graph:
  requires:
    - 01-01-PLAN.md (walking skeleton — SQLite schema, FastAPI app, price_history/fx_rates/settings tables)
    - 01-02-PLAN.md (portfolio import — DataFetcher reads holdings)
  provides:
    - GET /api/indices returning 4 indices with close, change_pct, date, market_label
    - GET /api/fx returning EUR/INR rate + 24h low/high + alert_threshold
    - POST /api/fx/alert persisting threshold to settings table
    - DataFetcher.fetch_indices() + fetch_fx_rate() with SQLite caching
    - get_market_reference_date(market) per NSE/XETRA/NYSE
    - IndicesCard + FXCard React components wired end-to-end
  affects:
    - 01-04-PLAN.md (briefing orchestrator reads indices and FX from price_history/fx_rates)
tech_stack:
  added:
    - zoneinfo (stdlib Python 3.9+) — timezone-aware reference date per market
    - yfinance multi-ticker download with threads=True
  patterns:
    - TDD RED/GREEN for Tasks 1 and 2 (failing tests committed before implementation)
    - Multi-ticker yfinance download with MultiIndex column slicing
    - Cache-first fallback pattern (live fetch → price_history cache → 503)
    - Parameterized ? SQL placeholders (T-03-01, T-03-05 mitigations)
    - Optional[float] instead of float | None (Python 3.9 compat)
key_files:
  created:
    - backend/core/timezone_utils.py
    - backend/core/data_fetcher.py
    - backend/api/indices.py
    - backend/api/fx.py
    - frontend/src/components/IndicesCard.jsx
    - frontend/src/components/FXCard.jsx
  modified:
    - backend/models.py (added IndexEntry, IndicesResponse, FXResponse, FXAlertRequest, FXAlertResponse)
    - backend/main.py (includes indices_router, fx_router)
    - frontend/src/api.js (added fetchIndices, fetchFX, setFXAlert)
    - frontend/src/App.jsx (added indices/fx state, IndicesCard, FXCard)
    - tests/test_api.py (added 13 new tests — 8 Task 1 + 5 Task 2)
decisions:
  - "Optional[float] instead of float | None union — Python 3.9 stdlib zoneinfo requires compat syntax"
  - "Cache fallback returns 503 with UI-SPEC error copy if both live and cache fail"
  - "fx_alert_threshold key hardcoded in fx.py — not from user input (T-03-05)"
  - "DataFetcher uses MultiIndex column slicing (xs) for multi-ticker yfinance response"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-13T18:58:00Z"
  tasks_completed: 3
  files_created: 6
  files_modified: 5
  tests_passing: 32
---

# Phase 01 Plan 03: Market Data Slice Summary

**One-liner:** yfinance multi-ticker indices fetch + EUR/INR FX rate with timezone-aware reference dates, SQLite caching, GET /api/indices + GET /api/fx + POST /api/fx/alert endpoints, and IndicesCard + FXCard React components.

---

## What Was Built

Complete market data vertical slice: yfinance fetches 4 indices and EUR/INR → caches to SQLite → served via FastAPI API → displayed in React with colored arrows and alert threshold UI.

- **backend/core/timezone_utils.py** — `get_market_reference_date(market, as_of)`: calculates correct reference date per market using zoneinfo. NSE closes 15:30 Asia/Kolkata, XETRA 17:30 Europe/Berlin, NYSE 16:00 America/New_York. Returns "YYYY-MM-DD" string.

- **backend/core/data_fetcher.py** — `DataFetcher` class:
  - `fetch_indices()`: downloads ^NSEI, ^BSESN, ^GDAXI, ^GSPC via `yf.download(threads=True)`, slices MultiIndex DataFrame with `xs()`, computes change_pct from last two rows, assigns timezone-correct reference date per market, caches to price_history via INSERT OR REPLACE.
  - `fetch_fx_rate(pair)`: uses `yf.Ticker(pair).history(period="2d")`, extracts rate/low/high/timestamp, caches to fx_rates via INSERT OR REPLACE.

- **backend/api/indices.py** — `GET /api/indices`: instantiates DataFetcher, calls fetch_indices(), returns `{indices: [...], fetched_at}`. Cache fallback loads last known close from price_history. If both fail: 503 with UI-SPEC exact error copy "Market data unavailable — {time}. Last updated: unknown. Retry in 1 minute."

- **backend/api/fx.py** — `GET /api/fx`: calls fetch_fx_rate(), reads alert_threshold from settings table (key="fx_alert_threshold"), returns FXResponse. `POST /api/fx/alert`: validates threshold > 0 (Pydantic + explicit check), INSERT OR REPLACE into settings table with hardcoded key (T-03-05).

- **backend/models.py** — Added Pydantic v2 models: `IndexEntry`, `IndicesResponse`, `FXResponse`, `FXAlertRequest` (with field_validator for threshold > 0), `FXAlertResponse`.

- **backend/main.py** — Includes `indices_router` and `fx_router`.

- **frontend/src/components/IndicesCard.jsx** — "Market Indices" heading (20px semibold), 4-row table: Name | Close (monospace) | Change (↑↓ colored green/red) | Date. "Market data unavailable" error state.

- **frontend/src/components/FXCard.jsx** — "EUR/INR" heading (20px semibold), rate in 28px monospace, 24h range "Low: {low} | High: {high}", timestamp "as of {time} IST" (12px caption), alert threshold section with set/edit input and "Alert threshold set" confirmation.

- **frontend/src/api.js** — Added `fetchIndices()`, `fetchFX()`, `setFXAlert(threshold)`.

- **frontend/src/App.jsx** — indices and fx state, loadIndices/loadFX on mount, handleSetAlert re-fetches FX, IndicesCard and FXCard placed below AllocationCard.

---

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for timezone_utils + DataFetcher | 8207228 | tests/test_api.py |
| 1 (GREEN) | timezone_utils.py + data_fetcher.py | 92f5da9 | backend/core/timezone_utils.py, backend/core/data_fetcher.py |
| 2 (RED) | Failing tests for API endpoints | 855dfc3 | tests/test_api.py |
| 2 (GREEN) | indices.py + fx.py + models + main.py | 0e69cef | backend/api/indices.py, backend/api/fx.py, backend/models.py, backend/main.py |
| 3 | React IndicesCard + FXCard components | d57ceb0 | frontend/src/components/IndicesCard.jsx, FXCard.jsx, api.js, App.jsx |

---

## Verification

All acceptance criteria met:

- `backend/core/timezone_utils.py` contains "ZoneInfo" and "Asia/Kolkata" — VERIFIED
- `backend/core/timezone_utils.py` raises ValueError for unknown market — VERIFIED (grep: 1 occurrence)
- `backend/core/data_fetcher.py` contains "yf.download" and "threads=True" — VERIFIED
- `backend/core/data_fetcher.py` contains "INSERT OR REPLACE INTO price_history" — VERIFIED
- `backend/core/data_fetcher.py` uses "?" as SQL placeholder — VERIFIED (zero f-string SQL)
- `backend/api/indices.py` contains "Market data unavailable" — VERIFIED
- `backend/api/fx.py` contains "fx_alert_threshold" — VERIFIED
- `backend/api/fx.py` contains "INSERT OR REPLACE INTO settings" with "?" — VERIFIED
- `backend/main.py` imports and includes both indices and fx routers — VERIFIED
- `backend/models.py` contains "class IndicesResponse" and "class FXResponse" — VERIFIED
- `frontend/src/components/IndicesCard.jsx` contains "Market Indices" heading — VERIFIED
- `frontend/src/components/IndicesCard.jsx` contains "Market data unavailable" — VERIFIED
- `frontend/src/components/FXCard.jsx` contains "EUR/INR" section heading — VERIFIED
- `frontend/src/components/FXCard.jsx` contains "Alert threshold" — VERIFIED
- `frontend/src/components/FXCard.jsx` contains "as of" and "IST" — VERIFIED
- `frontend/src/api.js` contains `fetch('/api/fx')` and `fetch('/api/indices')` — VERIFIED
- All 13 new pytest tests pass — VERIFIED (32/32 total)
- `npm run build` exits 0 — VERIFIED (205KB bundle)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Python 3.9 incompatible union type syntax**
- **Found during:** Task 2 GREEN phase (TypeError at module import)
- **Issue:** `float | None` union syntax was used in `backend/api/fx.py::_get_alert_threshold` return type annotation. Python 3.9 stdlib doesn't support `X | Y` union syntax — that requires Python 3.10+.
- **Fix:** Changed to `Optional[float]` with `from typing import Optional` import — semantically identical, compatible with Python 3.9+
- **Files modified:** backend/api/fx.py
- **Commit:** 0e69cef

---

## Known Stubs

None. All endpoints return real data:
- GET /api/indices fetches live from yfinance (with cache fallback)
- GET /api/fx fetches live EUR/INR from yfinance
- alert_threshold is null by default (correct — user hasn't set one yet)
- IndicesCard and FXCard render real API data with no hardcoded values

---

## Threat Surface Scan

All mitigations from the plan's `<threat_model>` are implemented:

| Threat | Mitigation Status |
|--------|-------------------|
| T-03-01 POST /api/fx/alert tampering | Pydantic FXAlertRequest field_validator enforces > 0; parameterized INSERT OR REPLACE into settings |
| T-03-02 yfinance data disclosure | Public market data; cached locally in SQLite on user's machine; no PII |
| T-03-03 yfinance MITM spoofing | Accepted (Phase 1 local app) |
| T-03-04 yfinance rate limiting DoS | Cache fallback in GET /api/indices: if live fetch fails, serves price_history cache |
| T-03-05 Settings table key injection | "fx_alert_threshold" hardcoded string in fx.py — not from user input |

No new threat surface introduced beyond what the plan modeled.

---

## TDD Gate Compliance

| Gate | Status |
|------|--------|
| Task 1 RED (test commit) | 8207228 — `test(01-03): add failing tests for timezone_utils, DataFetcher indices/FX (RED)` |
| Task 1 GREEN (feat commit) | 92f5da9 — `feat(01-03): implement DataFetcher + timezone_utils` |
| Task 2 RED (test commit) | 855dfc3 — `test(01-03): add failing tests for GET /api/indices, GET /api/fx, POST /api/fx/alert (RED)` |
| Task 2 GREEN (feat commit) | 0e69cef — `feat(01-03): indices + FX API endpoints` |

Both RED/GREEN gate sequences present in git log. TDD compliance: PASSED.

---

## Self-Check: PASSED

- backend/core/timezone_utils.py — FOUND
- backend/core/data_fetcher.py — FOUND
- backend/api/indices.py — FOUND
- backend/api/fx.py — FOUND
- backend/models.py — FOUND (updated with 5 new models)
- backend/main.py — FOUND (updated with 2 new routers)
- frontend/src/components/IndicesCard.jsx — FOUND
- frontend/src/components/FXCard.jsx — FOUND
- frontend/src/api.js — FOUND (updated)
- frontend/src/App.jsx — FOUND (updated)
- tests/test_api.py — FOUND (13 new tests, 32 total)
- Commit 8207228 (Task 1 RED) — FOUND
- Commit 92f5da9 (Task 1 GREEN) — FOUND
- Commit 855dfc3 (Task 2 RED) — FOUND
- Commit 0e69cef (Task 2 GREEN) — FOUND
- Commit d57ceb0 (Task 3) — FOUND
- 32/32 pytest tests passing — VERIFIED
- npm run build exits 0 — VERIFIED
