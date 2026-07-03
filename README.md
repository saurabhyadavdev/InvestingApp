# InvestIQ: Personal Cross-Border Investing Intelligence

**A daily briefing assistant for investors with holdings in India (Zerodha) and Germany (Trade Republic). Delivers structured portfolio insights, market indices, FX rates, and actionable buy/sell/hold guidance every morning.**

---

## What is InvestIQ?

**InvestIQ** is an open-source, local-first intelligence assistant that monitors your cross-border portfolio across Indian (Zerodha) and German (Trade Republic) brokers. It fetches daily OHLCV data, computes technical indicators (RSI, MACD, Bollinger Bands), aggregates news and analyst consensus, and synthesizes everything into a structured morning briefing — all running locally on your machine.

---

## Core Features

- **Automated Morning Briefing**: Daily briefing at 07:00 IST covering Nifty/Sensex, DAX, S&P 500, portfolio P&L, and recommended actions
- **Unified Portfolio View**: Holdings from Zerodha (India) and Trade Republic (Germany) in a single dashboard
- **EUR/INR FX Monitor**: Real-time exchange rate tracking for fund transfer timing decisions
- **Technical Signals + Analyst Consensus**: RSI, MACD, Bollinger Bands combined with Finnhub analyst ratings and price targets
- **AI-Powered Synthesis**: Claude API interprets technical + fundamental data into clear buy/sell/hold guidance
- **Local-First Privacy**: SQLite database stays on your machine — no portfolio data sent to third parties beyond public price lookups

---

## Getting Started

### Local Development

**1. Start the Backend (FastAPI):**

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure your environment
cp .env.example .env

# Run the development server
uvicorn backend.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.

**2. Start the Frontend (Vue.js):**

```bash
# In a new terminal, navigate to the frontend directory
cd frontend
npm install
npm run dev  # → http://localhost:3000
```

### Data Storage

SQLite database at `data/app.db` — created automatically on first startup. The `data/` directory is gitignored; your portfolio holdings stay local.

---

## Testing

```bash
pytest tests/ -v
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
