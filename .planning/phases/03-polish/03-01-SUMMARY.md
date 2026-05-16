---
plan: 03-01
phase: 03-polish
status: awaiting-human-checkpoint
tasks_completed: 2
tasks_total: 3
subsystem: portfolio-heatmap
tags: [frontend, backend, portfolio, daily-pct, heatmap]
depends_on: [02-04]
tech_stack:
  added: []
  patterns:
    - compute_daily_pct: SELECT close ORDER BY date DESC LIMIT 2 pattern
    - HeatMapCard: proportional flex tiles with semantic color thresholds
key_files:
  created:
    - backend/tests/test_portfolio_daily_pct.py
    - frontend/src/components/HeatMapCard.jsx
  modified:
    - backend/core/portfolio.py
    - backend/core/briefing.py
    - frontend/src/Dashboard.jsx
decisions:
  - name: daily_pct math approach
    choice: two-row DESC query from price_history; (close[0] - close[1]) / close[1] * 100
    rationale: Consistent with fetch_indices % change pattern in data_fetcher.py; DB-native, no yfinance re-fetch required
  - name: tile color thresholds
    choice: >=3 strong green, >=0 mild green, >=-3 mild red, else strong red, null neutral gray
    rationale: Matches UI-SPEC semantic palette; 3% threshold aligns with typical intraday significance
  - name: tile sizing
    choice: flex proportional width = (valueInr / totalValue * 100)% with minWidth 80
    rationale: Inline-styles-only approach per PATTERNS.md; no treemap library needed for MVP
metrics:
  duration_seconds: 420
  completed_date: "2026-05-16"
  tasks_completed: 2
  files_changed: 5
---

# Phase 3 Plan 01: Portfolio Heat Map Summary

**One-liner:** Proportional-flex heat map tiles sized by INR market value, colored by daily % change sourced from a two-row price_history query.

---

## What Was Built

### Task 1 — Backend: compute_daily_pct + briefing enrichment

`backend/core/portfolio.py` received a new top-level function `compute_daily_pct(db_path, ticker)`:

- Opens an sqlite3 connection and runs `SELECT close FROM price_history WHERE ticker = ? ORDER BY date DESC LIMIT 2`
- Returns `(rows[0][0] - rows[1][0]) / rows[1][0] * 100` when exactly two rows exist and `rows[1][0] != 0`
- Returns `None` for all edge cases: single row, zero rows, zero prev close, empty/None ticker
- Connection always closed in `finally` block

`backend/core/briefing.py` now:
- Imports `compute_daily_pct` alongside `get_portfolio_with_pl`
- Executes Step 3.5 after portfolio_data is populated: iterates `portfolio_data["holdings"]`, sets `holding["daily_pct"]` for each
- Falls back to `holding.setdefault("daily_pct", None)` for all holdings when the enrichment loop raises an exception (fail-open)

### Task 2 — Frontend: HeatMapCard + Dashboard wiring

`frontend/src/components/HeatMapCard.jsx`:
- Module-level `getTileColor(dailyPct)` with 5 bands: null → `#F5F5F5`, >=3 → `#E8F5E9`, >=0 → `#F1FBF2`, >=-3 → `#FFF3F4`, else → `#FFEBEE`
- `useMemo` computes per-tile `valueInr` (EUR converted via `fxRate`, INR as-is) and `totalValue`
- Filters out `asset_type === 'cash'`, `current_price == null`, `quantity <= 0`
- Empty state guard returns section with "No holdings to display heat map."
- Tile `width: calc({pct}% - 4px)` with `minWidth: 80`, `minHeight: 60`, `flexWrap: 'wrap'`
- `title` attribute: `{name || ticker} — {currencySymbol}{current_price}`
- Inline styles only; no new CSS files; no new npm packages

`frontend/src/Dashboard.jsx`:
- Added `import HeatMapCard from './components/HeatMapCard.jsx'`
- Added `<div className="portfolio-section"><HeatMapCard holdings={holdings} fxRate={fx?.rate ?? 90} /></div>` after AllocationCard

---

## Acceptance Criteria — Status

| Criterion | Status |
|-----------|--------|
| `backend/core/portfolio.py` contains `def compute_daily_pct(` | PASS |
| `backend/core/briefing.py` imports compute_daily_pct and contains `holding["daily_pct"]` | PASS |
| pytest test file exits 0 (7/7 tests pass) | PASS |
| HeatMapCard.jsx exists with getTileColor function | PASS |
| Contains `flexWrap: 'wrap'` and `minWidth: 80` and `daily_pct` and `title=` | PASS |
| Dashboard.jsx imports HeatMapCard and renders it | PASS |
| `npm run build` exits 0 | PASS |

---

## Edge Cases Observed

- Trade Republic holdings have `ticker_yfinance = None` until ISIN lookup is done. The enrichment loop handles this: `holding.get("ticker_yfinance") or holding.get("ticker")` falls back to `ticker_local` (the ISIN string), which won't match any price_history row, so `daily_pct = None`. The heat map renders those tiles in neutral gray.
- Zero-quantity holdings are filtered out by the tile computation (`quantity > 0`), so they never appear in the heat map.
- Holdings with `current_price = None` (no price data cached yet) are also filtered out.

---

## Deviations from Plan

### Auto-additions (Rule 2)

**1. [Rule 2 - Missing test] Added 7th test: correct row ordering**
- **Found during:** Task 1 test writing
- **Issue:** The plan specified 5 tests. An additional test was added to verify `ORDER BY date DESC LIMIT 2` correctly picks the most recent 2 rows when 3 are present (rows inserted in non-chronological order).
- **Fix:** Added `test_correct_row_order_used` test case.
- **Files modified:** backend/tests/test_portfolio_daily_pct.py
- **Commit:** ed6c0fd

All other aspects executed exactly as specified in the plan.

---

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 — Backend | ba134bf | feat(03-01): add compute_daily_pct to portfolio and briefing pipeline |
| 1 — Tests | ed6c0fd | test(03-01): add unit tests for compute_daily_pct |
| 2 — Frontend | 0a03552 | feat(03-01): add HeatMapCard component and wire into Dashboard |

---

## Self-Check

Files created:
- backend/tests/__init__.py — FOUND
- backend/tests/test_portfolio_daily_pct.py — FOUND
- frontend/src/components/HeatMapCard.jsx — FOUND

Commits:
- ba134bf — FOUND
- ed6c0fd — FOUND
- 0a03552 — FOUND

## Self-Check: PASSED

---

## Awaiting Human Checkpoint (Task 3)

The automated tasks are complete. Task 3 is a human-verify checkpoint: the user should start the backend and frontend servers, navigate to the dashboard, and visually verify:
1. The "Portfolio Heat Map" card appears below the Allocation card
2. Holdings render as proportional colored tiles
3. Tile colors reflect today's price movement (green/red/gray)
4. Hovering shows the holding name and current price in the browser tooltip
5. Holdings with no price data show neutral gray tiles
