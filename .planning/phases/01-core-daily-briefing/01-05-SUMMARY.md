---
phase: 01-core-daily-briefing
plan: 05
subsystem: portfolio
tags: [portfolio, usd, fx, pydantic, react, tdd]
dependency_graph:
  requires: [01-02, 01-03, 01-04]
  provides: [pl_usd per holding, total_usd aggregate, USD display in PortfolioTable]
  affects: [backend/core/portfolio.py, backend/models.py, backend/api/portfolio.py, backend/core/briefing.py, frontend/src/components/PortfolioTable.jsx, frontend/src/Dashboard.jsx]
tech_stack:
  added: []
  patterns: [TDD RED/GREEN, FX conversion via EURINR and USDINR rates, Pydantic default fields]
key_files:
  created: []
  modified:
    - backend/core/portfolio.py
    - backend/models.py
    - backend/api/portfolio.py
    - backend/core/briefing.py
    - frontend/src/components/PortfolioTable.jsx
    - frontend/src/Dashboard.jsx
    - tests/test_portfolio.py
    - tests/test_api.py
decisions:
  - EUR holding pl_usd derived from existing EURINR rate (not separate USDEUR fetch) to minimize API calls
  - USDINR cached in fx_rates table with 83.0 fallback; separate helper _get_cached_usdinr_rate added
  - total_usd accumulates market value (same pattern as total_inr/total_eur), not just P&L delta
  - USD display in tfoot shows "—" when totalUsd is 0 (no price data), matching plan requirement
metrics:
  duration: ~480s
  completed: "2026-05-13"
  tasks: 2
  files: 8
---

# Phase 01 Plan 05: USD P&L Summary

Closes gap PORT-04 / SC-05: added `pl_usd` per holding and `total_usd` aggregate to the portfolio slice, propagated through Pydantic models and the portfolio API endpoint, and displayed a USD total in the PortfolioTable summary row.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add pl_usd to get_portfolio_with_pl() and propagate through models | dd4011b | portfolio.py, models.py, api/portfolio.py, briefing.py, test_portfolio.py, test_api.py |
| 2 | Display USD total in PortfolioTable.jsx summary row | 214fb64 | PortfolioTable.jsx, Dashboard.jsx |

## What Was Built

- **get_portfolio_with_pl()** now accepts `fx_rate_usdinr: float = 83.0` parameter alongside the existing `fx_rate_eurinr`
- For INR holdings: `pl_usd = round(pl / fx_rate_usdinr, 2)`
- For EUR holdings: `pl_usd = round(pl * fx_rate_eurinr / fx_rate_usdinr, 2)` (via INR bridge)
- `total_usd` accumulates market value in USD (same pattern as `total_inr`/`total_eur`)
- **HoldingResponse** gains `pl_usd: float = 0.0` field
- **PortfolioResponse** gains `total_usd: float = 0.0` field
- **GET /api/portfolio** fetches cached USDINR rate (new `_get_cached_usdinr_rate()` helper) and passes it through
- **BriefingOrchestrator** fetches `USDINR=X` via yfinance (T-05-02: try/except with 83.0 fallback)
- **PortfolioTable.jsx** summary row now shows `($X.XX USD)` or `($— USD)` alongside EUR equiv
- **Dashboard.jsx** extracts `total_usd` from portfolio API response and passes as `totalUsd` prop

## Test Results

- 34 tests pass (34/34)
- 4 new tests added (RED gate committed separately before implementation)
- TDD gate: `test(01-05)` commit `202e14e` → `feat(01-05)` commit `dd4011b`

## TDD Gate Compliance

| Phase | Commit |
|-------|--------|
| RED (test) | 202e14e — failing tests for pl_usd/total_usd |
| GREEN (feat) | dd4011b — implementation passes all 4 new tests |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. USDINR rate flows only from trusted cached table (fx_rates) or yfinance — never from user input (T-05-01 mitigation satisfied). USDINR fetch failure falls back to 83.0 without blocking briefing generation (T-05-02 satisfied).

## Self-Check: PASSED

- backend/core/portfolio.py — FOUND
- backend/models.py — FOUND
- frontend/src/components/PortfolioTable.jsx — FOUND
- .planning/phases/01-core-daily-briefing/01-05-SUMMARY.md — FOUND
- Commit 202e14e (RED) — FOUND
- Commit dd4011b (GREEN) — FOUND
- Commit 214fb64 (Task 2) — FOUND
