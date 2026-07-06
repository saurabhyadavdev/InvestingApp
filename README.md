# InvestIQ: Personal Cross-Border Investing Intelligence

**A local-first daily briefing assistant for investors with holdings in India (Zerodha) and Germany (Trade Republic, Traders Place). Delivers structured portfolio insights, market indices, FX rates, news, and actionable buy/sell/hold guidance every morning.**

---

## What is InvestIQ?

**InvestIQ** is a personal, privacy-conscious investing cockpit for cross-border portfolios spanning **INR and EUR brokers**. It answers one question each morning:

> *What happened in the markets, how is my portfolio doing, and what should I do today?*

It imports holdings from broker CSVs (and PDF for Traders Place), fetches daily OHLCV data via yfinance, computes technical indicators (RSI, MACD, Bollinger Bands), aggregates news and analyst consensus, and synthesizes everything into a structured morning briefing — all running locally on your machine.

**Design constraints:** runs locally, SQLite for privacy, free-tier data APIs (yfinance, NewsAPI, Finnhub), no real-time tick data required.

---

## Core Features

- **Automated Morning Briefing**: Daily briefing at **08:55 Europe/Berlin** covering Nifty/Sensex, DAX, S&P 500, Nasdaq 100, portfolio P&L, and recommended actions
- **Unified Portfolio View**: Holdings from Zerodha (India), Trade Republic (Germany), and Traders Place (PDF) in a single dashboard
- **EUR/INR & USD/INR FX Monitor**: Exchange rate tracking for fund transfer timing decisions, with configurable alert thresholds
- **Technical Signals + Analyst Consensus**: RSI, MACD, Bollinger Bands combined with Finnhub analyst ratings and price targets
- **AI-Powered Synthesis**: Groq (Llama 3.3 70B) interprets technical + fundamental data into clear buy/sell/hold guidance with plain-English narratives
- **On-Demand Chat**: Follow-up questions against your portfolio context via `POST /api/chat`
- **Alerts & Watchlist**: Portfolio and FX alerts, trending stocks, buy recommendations, benchmark comparisons, and allocation heat map
- **Local-First Privacy**: SQLite database stays on your machine — no portfolio data sent to third parties beyond public price lookups

---

## Architecture

The central data pattern is the **briefing snapshot**: `BriefingOrchestrator` aggregates all data sources into one JSON blob stored in `briefing_snapshots`, and the frontend loads it via a single `GET /api/briefing` call.

```
Broker CSV/PDF Import
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  Python FastAPI (port 8000)                           │
│  ┌─────────────┐  ┌──────────────────┐  ┌─────────┐  │
│  │ REST API    │→ │ BriefingOrch.    │→ │ SQLite  │  │
│  │ /api/*      │  │ DataFetcher      │  │ app.db  │  │
│  └─────────────┘  │ AI Synthesis     │  └─────────┘  │
│                   │ APScheduler      │               │
│                   └────────┬─────────┘               │
└────────────────────────────┼──────────────────────────┘
                             │
              yfinance · NewsAPI · Finnhub · Groq
                             │
                             ▼
┌───────────────────────────────────────────────────────┐
│  React + Vite (port 3000)                             │
│  App.jsx → Dashboard.jsx → card components            │
└───────────────────────────────────────────────────────┘
```

**Operational flow:**

1. **Startup** — create DB schema, resolve Trade Republic ISINs → yfinance tickers, start scheduler, background price refresh or full briefing if today's snapshot is missing
2. **Scheduled job** — full briefing at 08:55 Europe/Berlin daily
3. **On open** — frontend shows cached snapshot immediately, then runs a lightweight price refresh in the background
4. **Manual refresh** — "Refresh Now" appears after noon or if the briefing is older than 6 hours

---

## Project Structure

```
InvestingApp/
├── backend/
│   ├── main.py              # FastAPI entry point, CORS, lifespan, scheduler
│   ├── config.py            # Environment-based settings
│   ├── database.py          # SQLite schema + migrations
│   ├── scheduler.py         # Daily morning briefing cron job
│   ├── models.py            # Pydantic response models
│   ├── api/                 # REST routers (one concern per file)
│   │   ├── briefing.py      # GET /api/briefing
│   │   ├── portfolio.py     # GET /api/portfolio, POST /api/import
│   │   ├── refresh.py       # POST /api/refresh, /api/refresh-prices
│   │   ├── indices.py       # GET /api/indices
│   │   ├── fx.py            # GET /api/fx, POST /api/fx/alert
│   │   ├── chat.py          # POST /api/chat
│   │   ├── alerts.py        # GET/POST /api/alerts
│   │   ├── stock.py         # Stock search and detail
│   │   ├── trending.py      # GET /api/trending
│   │   └── recommendations.py
│   ├── core/                # Business logic
│   │   ├── briefing.py      # BriefingOrchestrator
│   │   ├── data_fetcher.py  # yfinance, NewsAPI, Finnhub, indicators
│   │   ├── portfolio.py     # CSV/PDF import, P&L calculation
│   │   ├── ai_synthesis.py  # Rule-based signals + Groq narratives
│   │   └── alert_evaluator.py
│   └── tests/               # Backend-specific tests
├── frontend/
│   └── src/
│       ├── App.jsx          # Root — loads briefing, triggers price refresh
│       ├── Dashboard.jsx    # Unified morning briefing layout
│       ├── api.js           # Fetch wrapper for backend endpoints
│       └── components/      # PortfolioTable, FXCard, NewsCard, ChatPanel, etc.
├── tests/                   # Integration and unit tests
├── start.sh                 # One-command launcher (backend + frontend)
└── data/app.db              # SQLite database (gitignored, created on first run)
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/briefing` | GET | Latest cached briefing snapshot |
| `/api/refresh` | POST | Full briefing regeneration |
| `/api/refresh-prices` | POST | Lightweight price-only refresh |
| `/api/portfolio` | GET | Portfolio with P&L |
| `/api/import` | POST | CSV/PDF holdings import |
| `/api/indices` | GET | Market indices |
| `/api/fx` | GET | EUR/INR rate |
| `/api/fx/alert` | POST | Set FX alert threshold |
| `/api/alerts` | GET/POST | Portfolio and FX alerts |
| `/api/chat` | POST | Follow-up Q&A |
| `/api/trending` | GET | Trending stocks |
| `/api/stock/search` | GET | Stock lookup |
| `/api/stock/{ticker}/detail` | GET | Stock detail panel |
| `/api/recommendations` | GET | Buy recommendations |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+

### Environment Variables

Create a `.env` file in the project root:

```bash
# Optional — defaults shown
DB_PATH=data/app.db
HOST=127.0.0.1
PORT=8000

# Required for full functionality
NEWSAPI_KEY=your_newsapi_key
FINNHUB_KEY=your_finnhub_key
GROQ_API_KEY=your_groq_api_key
```

### Quick Start (launcher script)

```bash
./start.sh          # Starts backend + frontend, opens browser
./start.sh stop     # Stops all processes
```

The launcher auto-shuts down after 15 minutes. Backend logs go to `backend.log`, frontend logs to `frontend.log`.

### Local Development

**1. Start the Backend (FastAPI):**

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the development server
uvicorn backend.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.

**2. Start the Frontend (React + Vite):**

```bash
# In a new terminal, navigate to the frontend directory
cd frontend
npm install
npm run dev  # → http://localhost:3000
```

The Vite dev server proxies `/api` and `/health` requests to the backend on port 8000.

### Data Storage

SQLite database at `data/app.db` — created automatically on first startup. The `data/` directory is gitignored; your portfolio holdings stay local.

**Database tables:** `holdings`, `price_history`, `technical_indicators`, `fx_rates`, `briefing_snapshots`, `settings`, `chat_history`, `news_cache`, `analyst_cache`.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, APScheduler, SQLite |
| Frontend | React 19, Vite 8 |
| Market data | yfinance |
| Technical indicators | `ta` library (RSI, MACD, Bollinger Bands, SMAs) |
| News | NewsAPI |
| Analyst data | Finnhub |
| AI synthesis | Groq (Llama 3.3 70B) |
| PDF import | pdfplumber (Traders Place statements) |

---

## Testing

```bash
pytest tests/ -v              # Root-level integration and unit tests
pytest backend/tests/ -v      # Backend-specific tests
```

---

## License

This project is licensed under the MIT License.

---

## Contributing & Issues

Contributions, issues, and feature requests are welcome! Please check the issues page for ongoing work.

---

## Author

Created by **Saurabh Yadav**
