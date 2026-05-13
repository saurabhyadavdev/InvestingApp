# InvestIQ — Personal Cross-Border Investing Intelligence

## What This Is

A personal daily intelligence assistant for a cross-border investor with holdings in India (via Zerodha) and Germany (via Trade Republic, covering German stocks, US stocks, and ETFs). Every morning it delivers a structured briefing covering what markets did, relevant news, portfolio status, and concrete buy/sell/hold guidance — then stays available all day for on-demand questions and a mid-day refresh. The interface is a local web app with a chat layer for follow-up questions.

## Core Value

Every morning, give the user one place to understand their entire cross-border portfolio and know exactly what to do with it today.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Morning briefing: yesterday's performance for Nifty/Sensex, DAX, and S&P 500
- [ ] Important news filtered by relevance: holdings-specific, India macro, Germany macro, US/global macro
- [ ] Unified portfolio view across Zerodha (India) and Trade Republic (Germany) — P&L, current prices, positions
- [ ] Buy/Sell/Hold recommendations combining technical signals (RSI, MACD, moving averages) + analyst consensus + current position context
- [ ] AI synthesis opinion per holding in plain English alongside raw signal data
- [ ] EUR/INR exchange rate monitor with alerts when rate is favorable for transfer to India
- [ ] Idle cash detection across both portfolios with deployment suggestions
- [ ] Mid-day portfolio refresh on demand
- [ ] Chat interface for follow-up questions on any briefing topic
- [ ] Local web app dashboard — runs on laptop, accessible in browser

### Out of Scope

- Automated trade execution — advisory only, no order placement
- Real-time streaming prices (polling on morning/mid-day cadence is sufficient)
- Mobile app — local laptop web app is the target
- Multi-user / social features — single-user personal tool

## Context

**Portfolios:**
- India: Zerodha (NSE/BSE stocks) — data via CSV export or Kite API
- Germany: Trade Republic (German stocks, US stocks, ETFs) — data via CSV/PDF exports or manual holdings file
- EUR/INR currency conversion is a first-class concern: user actively decides when to transfer funds between Germany and India

**User's investing context:**
- Tracks three distinct market regions: India (IST timezone), Germany/EU (CET/CEST), US (ET)
- Holds a mix of individual stocks and ETFs
- Wants both technical and fundamental (analyst) signals before acting
- Morning briefing is the primary ritual — report runs before markets open in the user's local time

**Key data sources needed:**
- Market indices: NSE/BSE (Nifty 50, Sensex), XETRA/DAX, S&P 500
- Stock prices: yfinance or similar for NSE, XETRA, NYSE/NASDAQ tickers
- News: financial news APIs (e.g. NewsAPI, Bing News, Alpha Vantage news) filtered by company + macro themes
- Analyst data: ratings and price targets (e.g. from Yahoo Finance / Finviz)
- FX rates: EUR/INR live and historical (for transfer timing)
- Technical indicators: computed from OHLCV data (RSI, MACD, Bollinger Bands, MAs)

## Constraints

- **Runtime**: Local — no cloud hosting required for v1; runs on user's laptop
- **Data**: No real-time tick data; daily OHLCV + intraday snapshots are sufficient
- **Privacy**: Portfolio data stays local — no sending holdings to third-party services beyond price lookups
- **Cost**: Free/freemium data sources preferred (yfinance, free-tier APIs); avoid paid Bloomberg terminals
- **Tech**: Python backend preferred (yfinance ecosystem); web frontend (React or simple HTML) for local UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local web app, not hosted | Privacy — portfolio holdings stay on the user's machine | — Pending |
| Advisory only, no trade execution | Scope and safety — recommendations only | — Pending |
| Portfolio data via CSV export (not broker API) for Trade Republic | Trade Republic has no public API; CSV is the reliable path | — Pending |
| AI synthesis layer on top of raw signals | User wants both data and opinion — raw signals alone aren't enough | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-13 after initialization*
