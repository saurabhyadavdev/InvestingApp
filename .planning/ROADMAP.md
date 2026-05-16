# ROADMAP: InvestIQ

**Created:** 2026-05-13
**Granularity:** Coarse (3–5 phases)
**Mode:** MVP (vertical slices)
**Coverage:** 26/26 v1 requirements mapped

---

## Phases

- [x] **Phase 1: Core Daily Briefing** — Unified portfolio import and morning briefing with market indices
- [x] **Phase 2: Intelligence & Chat** — News, technical signals, AI synthesis, and chat interface (completed 2026-05-16)
- [x] **Phase 3: Polish** — Heat map, price/signal alerts, benchmark comparison (completed 2026-05-16)

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

**Plans:** 6/6 plans complete

Plans:

- [x] 01-01-PLAN.md — Walking Skeleton: FastAPI + React + SQLite schema + health endpoint + portfolio stub
- [x] 01-02-PLAN.md — CSV import + portfolio table + allocation card (PORT-01 through PORT-07)
- [x] 01-03-PLAN.md — Market indices + FX rate + alert threshold (MKT-01–03, FX-01–03)
- [x] 01-04-PLAN.md — Briefing orchestration + APScheduler + refresh + full dashboard (BRIEF-01–03)
- [x] 01-05-PLAN.md — Gap closure: USD P&L per holding + total_usd in portfolio response + PortfolioTable USD total (PORT-04)
- [x] 01-06-PLAN.md — Gap closure: FX alert crossing notification — alert_triggered flag + FXCard visual indicator (FX-02)

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

**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Foundation: replace pandas-ta with ta library, add news_cache + analyst_cache tables, extend Pydantic models with Phase 2 fields and chat models

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Backend pipeline: fetch_signals() + fetch_news() on DataFetcher; briefing steps 4+5 (SIG-01, MKT-04–07)
- [x] 02-03-PLAN.md — Frontend intelligence UI: PortfolioTable Rec badge + expandable row; NewsCard 4-tab; Dashboard Market Intelligence section (SIG-01, MKT-04–07)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-04-PLAN.md — Analyst + AI synthesis + Chat: fetch_analyst(), ai_synthesis.py, briefing steps 6+7, POST /api/chat, ChatPanel (SIG-02, SIG-03, SIG-04, BRIEF-04, BRIEF-05, FX-04)

**UI hint:** yes

---

### Phase 3: Polish

**Goal:** Enhance the daily briefing with richer visual insights and proactive monitoring — portfolio heat map (D-01–D-04), configurable price/signal alerts with browser notifications (D-05–D-07), and benchmark comparison against market indices (D-08–D-11).

**Mode:** mvp

**Depends on:** Phase 2

**Requirements:** D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11

**Success Criteria** (what must be TRUE):

1. User sees a Portfolio Heat Map card below AllocationCard with tiles sized by position value and colored by today's daily P&L %
2. Each heat map tile shows ticker + daily % change; hover/tap shows full holding name and current price
3. User can open an Alert Configuration modal via a gear icon in the dashboard header
4. User can configure four alert types: price target per holding, % daily move (global), RSI threshold (global), analyst rating change (global)
5. Alert configuration persists across briefings via the SQLite settings table; fx_alert_threshold is preserved
6. When alerts fire, a sticky amber AlertsBanner lists them at the top of the dashboard and matching PortfolioTable rows are highlighted amber
7. When alerts fire, an OS-level browser notification appears (Notification.requestPermission() called from gear-icon click, not useEffect)
8. User sees a Benchmark Comparison card below IndicesCard with a 1M/3M/YTD/1Y period switcher
9. Benchmark table compares My Portfolio %, Nifty 50, S&P 500, and DAX; regional rows compare India sub-portfolio vs Nifty and Germany/US/ETF vs S&P/DAX
10. Benchmark cells render green when portfolio beats the index, red when it lags, and "—" when historical data is unavailable

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Heat Map vertical slice: backend daily_pct via price_history + HeatMapCard.jsx + Dashboard wiring (D-01–D-04)

**Wave 2** *(blocked on Wave 1 completion — modifies briefing.py + Dashboard.jsx)*

- [x] 03-02-PLAN.md — Benchmark vertical slice: DataFetcher.fetch_benchmark + briefing step 7.5 + BenchmarkCard.jsx + Dashboard wiring (D-08–D-11)

**Wave 3** *(blocked on Wave 2 completion — modifies briefing.py + Dashboard.jsx + PortfolioTable.jsx)*

- [x] 03-03-PLAN.md — Alerts vertical slice: alert_evaluator + briefing step 4.5 + POST/GET /api/alerts + SettingsModal + AlertsBanner + PortfolioTable highlighting + browser Notification (D-05–D-07)

**UI hint:** yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Daily Briefing | 6/6 | Complete   | 2026-05-13 |
| 2. Intelligence & Chat | 4/4 | Complete   | 2026-05-16 |
| 3. Polish              | 3/3 | Complete   | 2026-05-16 |

---

## Summary

**Total v1 Requirements:** 26
**Mapped:** 26 ✓ (100% coverage)
**Orphaned:** 0

**Phase 1** (16 reqs) establishes the working briefing with portfolio import, unified view, indices, FX rates, and scheduled morning delivery.

**Phase 2** (10 reqs) adds the intelligence layer: holdings-specific and macro news, technical signals, analyst data, AI synthesis, and chat for follow-up questions.

**Phase 3** (11 decisions D-01–D-11) adds polish: portfolio heat map, configurable alerts with browser notifications, and benchmark comparison vs market indices.

This vertical-slice structure delivers a complete user workflow in Phase 1 (user can see their portfolio every morning) and extends with intelligence in Phase 2 (user knows what to do with it). Phase 3 sharpens monitoring (alerts) and adds context (heat map + benchmark).
