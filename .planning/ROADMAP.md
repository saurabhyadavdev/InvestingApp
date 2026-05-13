# ROADMAP: InvestIQ

**Created:** 2026-05-13
**Granularity:** Coarse (3–5 phases)
**Mode:** MVP (vertical slices)
**Coverage:** 26/26 v1 requirements mapped

---

## Phases

- [x] **Phase 1: Core Daily Briefing** — Unified portfolio import and morning briefing with market indices
- [x] **Phase 2: Intelligence & Chat** — News, technical signals, AI synthesis, and chat interface

---

## Phase Details

### Phase 1: Core Daily Briefing

**Goal:** User can import portfolios from Zerodha and Trade Republic, see a unified view with multi-currency P&L, view market indices, and receive a daily morning briefing at 07:00 IST with portfolio allocation and FX rates.

**Mode:** mvp

**Depends on:** Nothing (foundation phase)

**Requirements:** PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07, MKT-01, MKT-02, MKT-03, BRIEF-01, BRIEF-02, BRIEF-03, FX-01, FX-02, FX-03

**Success Criteria** (what must be TRUE):
1. User can import a Zerodha CSV and see all Indian positions with prices and P&L
2. User can import a Trade Republic CSV and see all German/US/ETF positions with prices and P&L
3. User can view unified portfolio showing both accounts on one screen with consolidated value and allocation
4. User can see yesterday's Nifty 50, Sensex, DAX, and S&P 500 closing prices and % change
5. User can see portfolio P&L in INR, EUR, and USD with currency-appropriate formatting
6. User can see idle cash balance per account (uninvested funds)
7. User can see allocation breakdown by region (India/Germany/US/ETF) and by asset type
8. User receives an auto-generated briefing at 07:00 IST without manual action
9. User can trigger a mid-day refresh and get updated prices within 1 minute
10. User can see current EUR/INR rate with timestamp and set an alert threshold for rate monitoring
11. User can view the complete briefing in a local web dashboard accessible via browser

**Plans:** 4/4 plans complete

Plans:
- [x] 01-01-PLAN.md — Walking Skeleton: FastAPI + React + SQLite schema + health endpoint + portfolio stub
- [x] 01-02-PLAN.md — CSV import + portfolio table + allocation card (PORT-01 through PORT-07)
- [x] 01-03-PLAN.md — Market indices + FX rate + alert threshold (MKT-01–03, FX-01–03)
- [x] 01-04-PLAN.md — Briefing orchestration + APScheduler + refresh + full dashboard (BRIEF-01–03)

**UI hint:** yes

---

### Phase 2: Intelligence & Chat

**Goal:** User receives holdings-specific news, technical signals (RSI/MACD/MAs), analyst consensus ratings, AI-synthesized investment guidance per holding, and can ask follow-up questions via chat constrained to current briefing data.

**Mode:** mvp

**Depends on:** Phase 1

**Requirements:** MKT-04, MKT-05, MKT-06, MKT-07, SIG-01, SIG-02, SIG-03, SIG-04, BRIEF-04, BRIEF-05, FX-04

**Success Criteria** (what must be TRUE):
1. User can see news filtered to companies in their portfolio (holdings-specific news)
2. User can see India macro news (RBI, budget, inflation, sector moves) and Germany/EU macro news (ECB, German economy) in the briefing
3. User can see US macro news (Fed, earnings season, global events affecting US stocks/ETFs)
4. User can see RSI, MACD, and moving average values per holding displayed in the briefing
5. User can see analyst consensus rating (Buy/Hold/Sell) and average price target per holding
6. User can see a combined Buy/Sell/Hold recommendation per holding that combines technical signals + analyst ratings + position context
7. User can see a plain-English AI explanation for each holding's recommendation (e.g., "Strong buy — RSI shows oversold + analyst upgrade to Buy")
8. User can ask follow-up questions about any holding, signal, or recommendation via chat interface
9. Chat responses reference only the current briefing data with no hallucinated facts or invented data
10. User can see cash deployment suggestions based on idle cash balance and market conditions

**Plans:** TBD

**UI hint:** yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Daily Briefing | 4/4 | Complete   | 2026-05-13 |
| 2. Intelligence & Chat | 0/1 | Not started | — |

---

## Summary

**Total v1 Requirements:** 26
**Mapped:** 26 ✓ (100% coverage)
**Orphaned:** 0

**Phase 1** (16 reqs) establishes the working briefing with portfolio import, unified view, indices, FX rates, and scheduled morning delivery.

**Phase 2** (10 reqs) adds the intelligence layer: holdings-specific and macro news, technical signals, analyst data, AI synthesis, and chat for follow-up questions.

This vertical-slice structure delivers a complete user workflow in Phase 1 (user can see their portfolio every morning) and extends with intelligence in Phase 2 (user knows what to do with it).
