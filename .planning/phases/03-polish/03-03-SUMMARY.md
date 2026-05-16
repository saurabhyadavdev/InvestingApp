---
plan: 03-03
phase: 03-polish
status: awaiting-human-checkpoint
tasks_completed: 4
tasks_total: 5
subsystem: alerts
tags: [alerts, settings, notifications, frontend, backend]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [alerts_fired in briefing, POST/GET /api/alerts, AlertsBanner, SettingsModal, PortfolioTable amber rows]
  affects: [briefing pipeline, frontend dashboard]
tech_stack:
  added: []
  patterns: [evaluate_alerts, INSERT OR REPLACE settings, sticky amber banner, modal overlay, useMemo alertTickers, useEffect notification dedup]
key_files:
  created:
    - backend/core/alert_evaluator.py
    - backend/api/alerts.py
    - backend/tests/test_alert_evaluator.py
    - backend/tests/test_alerts_api.py
    - frontend/src/components/AlertsBanner.jsx
    - frontend/src/components/SettingsModal.jsx
  modified:
    - backend/core/briefing.py
    - backend/main.py
    - frontend/src/api.js
    - frontend/src/components/PortfolioTable.jsx
    - frontend/src/Dashboard.jsx
decisions:
  - Daily move threshold uses abs() comparison — same threshold applies to both positive and negative moves (RESEARCH open-question #2 resolved: symmetric threshold)
  - Analyst-no-yesterday-row fallback: if prev rating is missing, do NOT fire — cannot determine a change occurred without baseline
  - Notification dedup via notifiedBriefingId state keyed on briefing.generated_at — same briefing never triggers more than one OS notification
  - requestPermission() called ONLY from handleOpenSettings (gear icon click, user gesture) — never from useEffect, per Chrome constraint
  - fx_alert_threshold preserved: alerts endpoint only writes alert_* keys, never reads/writes fx_alert_threshold
metrics:
  duration: ~20 minutes
  completed_date: "2026-05-16"
---

# Phase 3 Plan 03: Alerts & Settings Summary

**One-liner:** Configurable alerts pipeline (price/daily-move/RSI/analyst) with sticky amber banner, amber PortfolioTable rows, gear-icon settings modal, and OS-level browser notifications — all wired end-to-end from briefing step 6.5 through the dashboard.

---

## What Was Built

### Backend

**`backend/core/alert_evaluator.py`**
- `evaluate_alerts(holdings, signals, analyst_prev, analyst_curr, settings) -> list[dict]`
- Four alert types: `price`, `daily_move`, `rsi`, `analyst`
- Fail-open: per-ticker exceptions are caught and logged with `continue`; never raises
- Daily move: abs() comparison — threshold applies symmetrically to up and down moves
- Analyst change: graceful fallback when yesterday's row is missing (does NOT fire)

**`backend/core/briefing.py` — Step 6.5**
- New private helpers: `_load_alert_settings()` reads `alert_*` keys from settings table; `_load_yesterday_analyst()` queries `analyst_cache` for most recent date before today
- Step 6.5 inserted after analyst step 6 (analyst-change detection requires `analyst_curr`)
- `alerts_fired` key added to the briefing dict

**`backend/api/alerts.py`**
- `POST /api/alerts` — persists alert config via `INSERT OR REPLACE` per key; only writes `alert_*` namespace; `fx_alert_threshold` is never touched
- `GET /api/alerts` — reads all `alert_*` keys and reconstructs the same shape as the POST body
- Error handling: always returns JSON, never raises HTTP 500

**`backend/main.py`**
- `alerts_router` imported and registered with `app.include_router(alerts_router)`

### Tests

**28 unit tests passing** across two suites:
- `test_alert_evaluator.py`: 8 positive + negative cases per alert type, plus analyst-no-yesterday fallback, multi-holding, and empty-settings edge cases
- `test_alerts_api.py`: POST writes expected keys, POST does NOT clobber `fx_alert_threshold`, GET round-trips saved values

### Frontend

**`frontend/src/api.js`**
- `saveAlertSettings(settings)` — POST `/api/alerts`
- `fetchAlertSettings()` — GET `/api/alerts`
Both follow the `setFXAlert` error-handling pattern exactly.

**`frontend/src/components/AlertsBanner.jsx`**
- Sticky amber banner (`position: sticky`, `top: 0`, `zIndex: 100`)
- Returns `null` when `alertsFired` is empty
- Dismiss button (×) hides for the session; re-appears on next briefing load
- `role="alert"` for screen reader announcement

**`frontend/src/components/SettingsModal.jsx`**
- Modal overlay with `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Escape key handler via `useEffect` cleanup
- Backdrop click to close (target === currentTarget)
- Four sections: Price Target Alerts, Daily Move Alerts, RSI Alerts, Analyst Rating Alerts
- Per-field validation: positive number check for prices, 0–100 range for daily move %
- Save success/error toast (3-second auto-dismiss)
- "Save Alert Settings" button calls `saveAlertSettings` from api.js

**`frontend/src/components/PortfolioTable.jsx`**
- `alertTickers` prop (Set or array); defaults to empty Set
- Rows with an alerted ticker get `background: rgba(255, 193, 7, 0.12)` (amber tint)

**`frontend/src/Dashboard.jsx`**
- Imports: `AlertsBanner`, `SettingsModal`, `fetchAlertSettings`, `useMemo`, `useEffect`
- State: `isSettingsOpen`, `alertInitialSettings`, `notifiedBriefingId`
- `alertsFired = briefing?.alerts_fired ?? []` derived before conditional returns
- `alertTickers` computed via `useMemo` from `alertsFired`
- Gear icon (⚙) in header right; `handleOpenSettings` calls `Notification.requestPermission()` then `fetchAlertSettings()`
- `<AlertsBanner>` placed sticky above Import CSV section
- `<PortfolioTable alertTickers={alertTickers}>` for amber row highlighting
- `<SettingsModal>` mounted at bottom of page JSX
- `useEffect` fires `new Notification('InvestIQ Alert', {...})` once per unique `generated_at` when `Notification.permission === 'granted'` — deduped by `notifiedBriefingId` state

---

## Key Design Decisions

| Decision | Detail |
|----------|--------|
| Daily move threshold | Symmetric (abs() comparison) — one threshold for both up and down moves |
| Analyst baseline | If `analyst_prev[ticker]` is absent, alert does NOT fire — no false positives |
| Notification dedup | Keyed on `briefing.generated_at` — same briefing never triggers twice per session |
| `requestPermission` placement | Gear icon `onClick` only, never in `useEffect` — Chrome blocks non-user-gesture calls |
| `fx_alert_threshold` preservation | Alerts POST only writes `alert_*` keys; tested explicitly in test suite |

---

## Deviations from Plan

None — plan executed exactly as written. The PLAN.md task description and the plan's interface spec were aligned; all acceptance criteria are met.

---

## Self-Check

- `backend/core/alert_evaluator.py` — created ✓
- `backend/api/alerts.py` — created ✓
- `backend/tests/test_alert_evaluator.py` — created, 28 tests pass ✓
- `backend/tests/test_alerts_api.py` — created ✓
- `backend/core/briefing.py` — step 6.5 added, `alerts_fired` in briefing dict ✓
- `backend/main.py` — `alerts_router` registered ✓
- `frontend/src/api.js` — `saveAlertSettings` + `fetchAlertSettings` ✓
- `frontend/src/components/AlertsBanner.jsx` — created ✓
- `frontend/src/components/SettingsModal.jsx` — created ✓
- `frontend/src/components/PortfolioTable.jsx` — `alertTickers` prop added ✓
- `frontend/src/Dashboard.jsx` — all wiring complete ✓
- Frontend build: 0 errors ✓
- `requestPermission` NOT in any `useEffect` ✓
- `fx_alert_threshold` never referenced in `backend/api/alerts.py` code (only in docstrings) ✓
