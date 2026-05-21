---
phase: 04-on-demand-stock-detail
plan: "01"
subsystem: backend
tags: [api, ai-synthesis, models, stock-detail]
dependency_graph:
  requires: []
  provides: [GET /api/stock/{ticker}/detail]
  affects: [backend/models.py, backend/core/ai_synthesis.py, backend/main.py]
tech_stack:
  added: []
  patterns: [graceful-null-fallback, Groq-API-key-guard]
key_files:
  created:
    - backend/api/stock.py
  modified:
    - backend/models.py
    - backend/core/ai_synthesis.py
    - backend/main.py
decisions:
  - Used settings.GROQ_API_KEY guard matching existing chat.py pattern — no key means StockDetailAI with all nulls
  - synthesise_holding_ondemand is separate from synthesise_holding to avoid breaking briefing path
metrics:
  duration: ~8 minutes
  completed_date: "2026-05-21"
  tasks_completed: 2
  files_changed: 4
---

# Phase 04 Plan 01: Backend On-Demand Stock Detail Endpoint Summary

**One-liner:** `GET /api/stock/{ticker}/detail` returning signals, analyst data, and three-section AI narrative (today_move / recommendation / outlook).

## What Was Built

- `StockDetailAI` and `StockDetailResponse` Pydantic v2 models added to `backend/models.py`
- `synthesise_holding_ondemand(client, ticker, signals, analyst, recent_news) -> dict` added to `backend/core/ai_synthesis.py` — returns structured three-key dict, never raises
- `backend/api/stock.py` created with `GET /api/stock/{ticker}/detail` — fetches live signals + analyst + news, runs AI synthesis if GROQ_API_KEY set, returns nulls gracefully on any failure

## Verification Results

- Import check: `from backend.models import StockDetailResponse, StockDetailAI; from backend.core.ai_synthesis import synthesise_holding_ondemand` — PASSED
- Router check: `router.routes` contains `/api/stock/{ticker}/detail` — PASSED
- `backend/main.py` imports `stock_router` and registers it after `trending_router` — PASSED

## Key Interfaces

```
StockDetailResponse
  ticker: str
  signals: Optional[dict]   # {rsi_14, macd, macd_signal, macd_histogram, sma_50, sma_200}
  analyst: Optional[dict]   # {rating, target_mean, num_analysts}
  ai: Optional[StockDetailAI]
    today_move: Optional[str]
    recommendation: Optional[str]
    outlook: Optional[str]
  rec: Optional[str]        # "BUY" | "HOLD" | "SELL"

Endpoint: GET /api/stock/{ticker}/detail
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | 01abffb | feat(models): add StockDetailResponse and synthesise_holding_ondemand |
| 2    | a9777ad | feat(api): add GET /api/stock/{ticker}/detail endpoint |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `backend/api/stock.py` exists: FOUND
- `backend/models.py` contains `StockDetailResponse`: FOUND
- `backend/core/ai_synthesis.py` contains `synthesise_holding_ondemand`: FOUND
- Commits 01abffb and a9777ad exist: FOUND
