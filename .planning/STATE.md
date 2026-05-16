---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: ready_to_plan
last_updated: "2026-05-13T21:49:26.277Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# STATE: InvestIQ

**Initialized:** 2026-05-13
**Status:** Ready to plan

---

## Project Reference

**Core Value:** Every morning, give the user one place to understand their entire cross-border portfolio and know exactly what to do with it today.

**Scope:** Personal cross-border investing assistant for user with holdings across:

- India: Zerodha (NSE/BSE stocks)
- Germany: Trade Republic (German stocks, US stocks, ETFs)

**Critical Constraint:** Portfolio data stays local — no cloud hosting, no sending holdings to external services.

---

## Current Position

Phase: 01 (core-daily-briefing) — EXECUTING
Plan: Not started
**Milestone:** MVP (vertical slices)
**Phase:** 02
**Progress:** [██████████] 100%

### Roadmap

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 1 | Core Daily Briefing (portfolio + indices + FX) | 16 | Not started |
| 2 | Intelligence & Chat (news + signals + AI + chat) | 10 | Not started |

---

## Performance Metrics

### Coverage

- **v1 Requirements:** 26 total, 26 mapped, 0 orphaned (100% ✓)
- **Phase 1:** 16 requirements
- **Phase 2:** 10 requirements

### Complexity Estimates (from research)

- **Phase 1 MVP:** 2–3 weeks
- **Phase 1 + 2 (full featured):** 6–8 weeks
- **Phase 3 Polish:** +2–3 weeks (deferred; out of scope for MVP)

---

## Accumulated Context

### Architecture Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| **ISIN as canonical identifier** | Tickers vary across brokers; ISIN is universal | Locked |
| **FastAPI backend** | Async, lightweight, persistent chat, local REST + WebSocket | Locked |
| **SQLite database** | File-based, no server, single-file backup | Locked |
| **Claude API (Haiku 4.5)** | Cost-effective reasoning for finance; ~$0.01–0.05/briefing | Locked |
| **yfinance + Finnhub** | Unified API for all markets, free, no auth required | Locked |
| **pandas-ta for indicators** | 110+ indicators, pure Python, actively maintained | Locked |
| **APScheduler** | In-process scheduler, integrates with FastAPI | Locked |
| **React + Vite frontend** | Polished dashboard + chat; vanilla HTML fallback if needed | Locked |
| **CSV import (not broker OAuth)** | Trade Republic has no public API; Zerodha OAuth adds complexity | Locked |
| Phase 01-core-daily-briefing P03 | 317s | 3 tasks | 11 files |
| Phase 01 P04 | 241s | 2 tasks | 10 files |
| Phase 01-core-daily-briefing P05 | 480 | 2 tasks | 8 files |

### Critical Pitfalls & Prevention

| Pitfall | Phase | Prevention |
|---------|-------|-----------|
| NSE/BSE ticker mismatch | Phase 1 | Build Zerodha → ISIN → yfinance mapping; use ISIN as canonical |
| Multi-timezone misalignment | Phase 1 | Store UTC internally; calculate reference date per market independently |
| AI hallucination (Phase 2) | Phase 2 | Strict prompt ("only provided data"); JSON-structured inputs; output validation |
| Free API degradation | Phase 2 | Freshness monitoring; graceful degradation; cache aggressively |

### Stack Summary

| Component | Choice | Why |
|-----------|--------|-----|
| Stock data | yfinance 0.2.40+ (primary), nsepython fallback | Unified API for all markets |
| Technical indicators | pandas-ta 0.3.14b+ | 110+ indicators, pure Python |
| News | NewsAPI (100 req/day) + Finnhub (60 req/min) | Dual-purpose: news + analyst data |
| FX rates | yfinance `EURINR=X` | Simple, free, daily transfer timing |
| AI synthesis | Claude API (Haiku 4.5 for cost) | Best financial reasoning, low cost |
| Backend | FastAPI 0.104+ | Async, lightweight, persistent chat |
| Database | SQLite | File-based, no external server |
| Scheduler | APScheduler | In-process, integrates with FastAPI |
| Frontend | React + Vite | Polished dashboard + chat |

---

## Key Dates

- **Roadmap Created:** 2026-05-13
- **Phase 1 Target:** 2–3 weeks from start
- **Phase 2 Target:** +3–4 weeks after Phase 1
- **Full MVP Target:** ~6–8 weeks

---

## Session Continuity

Last session: 2026-05-14T08:50:53Z
Stopped at: Code review fixes applied (c411b25). Pausing for browser UAT sign-off.
Resume file: .planning/phases/01-core-daily-briefing/.continue-here.md

### After Phase 1 Transition

1. Move validated requirements to PROJECT.md "Validated" section
2. Update any requirements that failed validation
3. Note any new requirements discovered during implementation
4. Check if Phase 2 needs adjustment based on Phase 1 learnings

### After Phase 2 Transition

1. Review out-of-scope list (v2 features remain unchanged)
2. Decide on Phase 3 (Polish: heat map, alerts, benchmark comparison)
3. Option to ship v1 without Phase 3 or continue

---

## Open Questions

None yet. Roadmap is locked and awaiting execution.

---

*STATE initialized: 2026-05-13 after ROADMAP creation*
