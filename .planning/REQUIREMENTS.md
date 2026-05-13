# Requirements: InvestIQ

**Defined:** 2026-05-13
**Core Value:** Every morning, give the user one place to understand their entire cross-border portfolio and know exactly what to do with it today.

## v1 Requirements

### Portfolio

- [x] **PORT-01**: User can import Zerodha holdings via CSV and see all Indian positions
- [x] **PORT-02**: User can import Trade Republic holdings via CSV and see all German/US/ETF positions
- [x] **PORT-03**: User can view unified portfolio showing both accounts on one screen
- [x] **PORT-04**: User can see unrealized P&L per holding in INR, EUR, and USD
- [x] **PORT-05**: User can see total portfolio value and P&L in each currency (INR/EUR/USD)
- [x] **PORT-06**: User can see portfolio allocation breakdown by region (India / Germany / US / ETF) and by asset type
- [x] **PORT-07**: User can see idle cash balance per account (uninvested funds)

### Market Data

- [x] **MKT-01**: User can see yesterday's closing performance for Nifty 50 and Sensex (direction + % change)
- [x] **MKT-02**: User can see yesterday's closing performance for DAX (direction + % change)
- [x] **MKT-03**: User can see yesterday's closing performance for S&P 500 (direction + % change)
- [ ] **MKT-04**: User can see news filtered to companies in their portfolio (holdings-specific news)
- [ ] **MKT-05**: User can see India macro news (RBI, budget, inflation, sector moves)
- [ ] **MKT-06**: User can see Germany/EU macro news (ECB, German economy, DAX events)
- [ ] **MKT-07**: User can see US macro news (Fed, earnings season, global events affecting US stocks/ETFs)

### FX & Cash Management

- [x] **FX-01**: User can see current EUR/INR exchange rate with timestamp
- [x] **FX-02**: User can set an EUR/INR alert threshold and be notified when rate crosses it
- [x] **FX-03**: User can see today's EUR/INR range (low–high) to assess transfer timing
- [ ] **FX-04**: User can see suggestions for deploying idle cash (where to put uninvested funds)

### Signals & Recommendations

- [ ] **SIG-01**: User can see RSI, MACD, and moving average values per holding
- [ ] **SIG-02**: User can see analyst consensus rating (Buy/Hold/Sell) and average price target per holding
- [ ] **SIG-03**: User can see a Buy/Sell/Hold recommendation per holding combining technical + analyst signals
- [ ] **SIG-04**: User can see a plain-English AI synthesis explaining the recommendation for each holding

### Briefing & Interface

- [x] **BRIEF-01**: Morning briefing auto-generates at 07:00 IST without user action
- [x] **BRIEF-02**: User can trigger an on-demand mid-day refresh anytime
- [x] **BRIEF-03**: User can view the complete briefing in a local web dashboard (opens in browser)
- [ ] **BRIEF-04**: User can ask follow-up questions about any holding, signal, or recommendation via chat
- [ ] **BRIEF-05**: Chat responses reference only the current briefing data (no hallucinated facts)

## v2 Requirements

### Advanced Analysis

- **ADV-01**: User can see portfolio performance vs benchmarks (Nifty, DAX, S&P 500) YTD
- **ADV-02**: User can see portfolio heat map showing concentration risk by sector and region
- **ADV-03**: User can set custom alert rules (e.g., holding drops >10% in a day)
- **ADV-04**: User can see upcoming dividend dates and expected amounts per holding
- **ADV-05**: User can see historical portfolio P&L chart over time

### Export & Notifications

- **EXP-01**: User can export the morning briefing as PDF
- **EXP-02**: User can receive morning briefing via email

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated trade execution | Advisory only — no order placement, no regulatory risk |
| Real-time streaming prices | Daily polling + on-demand refresh is sufficient; streaming adds infrastructure complexity |
| Mobile app | Local laptop web app covers core use case; mobile is a separate platform |
| Multi-user / social features | Single-user personal tool; no social features, follower counts, etc. |
| Tax optimization | Too jurisdiction-specific (India capital gains rules differ from Germany/US); deferred |
| Options chain analysis | Equity/ETF focus only for v1 |
| Crypto holdings | Not in scope — user holds stocks and ETFs only |
| Broker OAuth / direct API linking | Trade Republic has no public API; Zerodha API adds auth complexity; CSV is reliable path |
| Backtesting signals | Interesting but not core to daily intelligence use case; v3+ |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PORT-01 | Phase 1 | Complete |
| PORT-02 | Phase 1 | Complete |
| PORT-03 | Phase 1 | Complete |
| PORT-04 | Phase 1 | Complete |
| PORT-05 | Phase 1 | Complete |
| PORT-06 | Phase 1 | Complete |
| PORT-07 | Phase 1 | Complete |
| MKT-01 | Phase 1 | Complete |
| MKT-02 | Phase 1 | Complete |
| MKT-03 | Phase 1 | Complete |
| BRIEF-01 | Phase 1 | Complete |
| BRIEF-02 | Phase 1 | Complete |
| BRIEF-03 | Phase 1 | Complete |
| FX-01 | Phase 1 | Complete |
| FX-02 | Phase 1 | Complete |
| FX-03 | Phase 1 | Complete |
| MKT-04 | Phase 2 | Pending |
| MKT-05 | Phase 2 | Pending |
| MKT-06 | Phase 2 | Pending |
| MKT-07 | Phase 2 | Pending |
| SIG-01 | Phase 2 | Pending |
| SIG-02 | Phase 2 | Pending |
| SIG-03 | Phase 2 | Pending |
| SIG-04 | Phase 2 | Pending |
| BRIEF-04 | Phase 2 | Pending |
| BRIEF-05 | Phase 2 | Pending |
| FX-04 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---

*Requirements defined: 2026-05-13*
*Roadmap traceability: 2026-05-13 after phase identification*
