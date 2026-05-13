# InvestIQ

Personal cross-border investing intelligence assistant for investors with holdings in India (Zerodha) and Germany (Trade Republic). Delivers a structured daily briefing every morning covering portfolio status, market indices, FX rates, and actionable buy/sell/hold guidance.

## Overview

- Morning briefing at 07:00 IST covering Nifty/Sensex, DAX, and S&P 500
- Unified portfolio view across Zerodha (India) and Trade Republic (Germany)
- EUR/INR exchange rate monitor for fund transfer timing
- Technical signals (RSI, MACD, Bollinger Bands) + analyst consensus
- Local web app — portfolio data stays on your machine

## Installation

```bash
# Backend (Python)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Copy environment template and fill in API keys
cp .env.example .env

# Frontend (Node.js)
cd frontend
npm install
cd ..
```

## Running

```bash
# Backend (in project root)
uvicorn backend.main:app --reload --port 8000

# Frontend (in a separate terminal)
cd frontend
npm run dev  # → http://localhost:3000
```

## Data Storage

SQLite database at `data/app.db` — created automatically on first startup. The `data/` directory is gitignored; your portfolio holdings stay local.

For best security, store the project in an encrypted volume (FileVault on macOS, BitLocker on Windows).

## Testing

```bash
pytest tests/ -v
```
