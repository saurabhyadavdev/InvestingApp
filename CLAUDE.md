<!-- GSD:project-start source:PROJECT.md -->
## Project

**InvestIQ — Personal Cross-Border Investing Intelligence**

A personal daily intelligence assistant for a cross-border investor with holdings in India (via Zerodha) and Germany (via Trade Republic, covering German stocks, US stocks, and ETFs). Every morning it delivers a structured briefing covering what markets did, relevant news, portfolio status, and concrete buy/sell/hold guidance — then stays available all day for on-demand questions and a mid-day refresh. The interface is a local web app with a chat layer for follow-up questions.

**Core Value:** Every morning, give the user one place to understand their entire cross-border portfolio and know exactly what to do with it today.

### Constraints

- **Runtime**: Local — no cloud hosting required for v1; runs on user's laptop
- **Data**: No real-time tick data; daily OHLCV + intraday snapshots are sufficient
- **Privacy**: Portfolio data stays local — no sending holdings to third-party services beyond price lookups
- **Cost**: Free/freemium data sources preferred (yfinance, free-tier APIs); avoid paid Bloomberg terminals
- **Tech**: Python backend preferred (yfinance ecosystem); web frontend (React or simple HTML) for local UI
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Executive Summary
- **Data fetching:** yfinance (primary, unified) + nsepython (fallback for NSE reliability)
- **Technical indicators:** pandas-ta (110+ indicators, vectorized, pure Python)
- **News:** NewsAPI (100 req/day free tier) + Finnhub
- **Analyst data:** Finnhub (60 req/min free tier — ratings, price targets)
- **FX rates:** yfinance (`EURINR=X`)
- **Backend:** FastAPI (async, lightweight, perfect for local app)
- **Frontend:** React + Vite (or vanilla HTML if minimal)
- **AI synthesis:** Claude API (~$0.01–0.05 per briefing)
- **Database:** SQLite (file-based, no external server)
## Stock Data
### Primary: yfinance 0.2.40+
- Covers NSE/BSE (via `.NS` suffix), XETRA, US stocks, indices
- Unified API: Nifty (`^NSEI`), Sensex (`^BSESN`), DAX (`^GDAXI`), S&P 500 (`^GSPC`)
- Free, no authentication; 10–15 min delay on NSE (acceptable for daily briefing)
- **Confidence: HIGH**
### Fallback: nsepython 0.1.1+
- Direct NSE connection, near real-time, higher reliability for NSE-specific quirks
- Use if yfinance NSE latency becomes an issue
- **Confidence: MEDIUM-HIGH**
### Do NOT use:
- **Jugaad-trader** — unmaintained since ~2021, breaks with NSE API changes
- **py-nsetools** — deprecated, superseded by nsepython
## Technical Indicators
### Primary: pandas-ta 0.3.14b+
- 110+ indicators: RSI, MACD, Bollinger Bands, SMA, EMA, ATR, ADX, etc.
- Pure Python (no C compilation required)
- Integrates seamlessly with pandas DataFrames
- Actively maintained
- **Confidence: HIGH**
### Do NOT use:
- **TA-Lib** — C-based, requires compilation; overkill for daily indicators
- **Tulipy** — abandoned
## News Aggregation
### Primary: NewsAPI (newsapi.org)
- 100 free requests/day — sufficient for ~14 news fetches per morning
- Good coverage of Indian stocks, global stocks, financial news
- Python package: `newsapi-python`
- Strategy: 1 call per holding + 2–3 calls for macro themes (India, Germany, US)
- **Confidence: HIGH**
### Secondary: Finnhub (finnhub.io)
- 60 req/min free tier (more generous than NewsAPI)
- Also provides analyst ratings, price targets, earnings dates — dual-purpose
- Python package: `finnhub-python`
- **Confidence: HIGH**
### Do NOT use:
- **Bing News API** — removed from Azure in 2023
- **Web scraping** — brittle; only emergency fallback
## Analyst Ratings & Price Targets
### Primary: Finnhub API
- Structured data: analyst recommendations, target prices, earnings calendar
- Free tier: 60 req/min
- Decent coverage including NSE stocks
- **Confidence: HIGH**
### Secondary: yfinance `.info` / `.recommendations`
- Unofficial; ratings often lag; acceptable as fallback only
## Currency / FX Rates
### Primary: yfinance
- `yf.download('EURINR=X')` — EUR/INR daily and intraday
- Simple, free, sufficient for daily transfer-timing decisions
- **Confidence: HIGH**
## Backend
### Primary: FastAPI 0.104+
- Modern Python web framework (async, type hints, built-in OpenAPI docs)
- Lightweight — runs easily on a laptop
- Suitable for REST API serving briefings, portfolio data, chat
## Frontend
### Option A: React + Vite (recommended for polished dashboard)
- Modern, fast build tool; good for chat interface + dynamic updates
- `npm create vite@latest frontend -- --template react`
### Option B: Vanilla HTML + Fetch API (minimal dependencies)
- No build step, no Node.js required
- Sufficient for simple briefing display
## AI Synthesis
### Primary: Claude API (Anthropic)
- Best reasoning for financial synthesis (interpreting RSI + MACD + analyst targets)
- ~$0.01–0.05 per briefing → ~$2–4/month for daily use
- Python package: `anthropic`
- Use claude-haiku-4-5 for cost efficiency; claude-sonnet-4-6 for higher quality synthesis
- **Confidence: HIGH**
### Do NOT use:
- **Ollama (local LLM)** — reasoning quality insufficient for reliable financial synthesis
## Database
### Primary: SQLite
- File-based, no external server required
- Built into Python (`sqlite3` standard library)
- Easy backup (single `.db` file)
- `holdings` — ticker, quantity, avg_buy_price, currency, broker
- `prices` — daily OHLCV cache per ticker
- `indicators` — RSI, MACD, BB, SMA cached per ticker per date
- `news` — news archive filtered by holding
- `fx_rates` — EUR/INR historical snapshots
## Scheduler
### Primary: APScheduler or Python `schedule` library
- Run morning briefing at 6 AM local time automatically
- `schedule>=1.2.0` is simpler; APScheduler is more robust
## Key Implementation Notes
## Installation
## Confidence Summary
| Component | Confidence |
|-----------|-----------|
| yfinance (stock data) | HIGH |
| pandas-ta (indicators) | HIGH |
| NewsAPI (news) | HIGH |
| Finnhub (analyst data) | HIGH |
| yfinance (FX rates) | HIGH |
| FastAPI (backend) | HIGH |
| Claude API (synthesis) | HIGH |
| SQLite (database) | HIGH |
| nsepython (NSE fallback) | MEDIUM-HIGH |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
