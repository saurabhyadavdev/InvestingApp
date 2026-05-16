# Phase 2: Intelligence & Chat - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 adds a per-holding intelligence layer to the existing morning briefing: news (holdings-specific + macro), technical signals (RSI/MACD/MAs), analyst consensus (rating + price target), AI-synthesised Buy/Hold/Sell recommendations in plain English, and a conversational chat panel constrained to the current briefing data.

Phase 1 output (portfolio table, indices, FX card, briefing orchestration) is the foundation — Phase 2 enriches it without replacing it.

</domain>

<decisions>
## Implementation Decisions

### Signal Display
- **D-01:** Add a **colour-coded Rec badge** as a new column in the existing portfolio table — green BUY, grey HOLD, red SELL. Visible at a glance without expanding.
- **D-02:** Signal numbers (RSI, MACD, SMA50, SMA200) are shown **only inside the expanded row**, not as additional table columns. Table stays clean.
- **D-03:** Expanding a holding row reveals: signal numbers + analyst consensus (rating + price target) + AI narrative (2–3 sentences). No separate signals section needed.

### AI Synthesis
- **D-04:** AI narrative lives **inside the expanded holding row**, below the signal numbers. No separate "Briefing Intelligence" card.
- **D-05:** Length is **2–3 sentences** per holding — enough to state the signal reading, analyst stance, and actionable conclusion. Not a one-liner, not a paragraph.
- **D-06:** AI synthesis runs for **all holdings at briefing generation time** (not on-demand). Pre-generated and stored in the briefing snapshot. Adds ~$0.01–0.03 per briefing in Haiku costs.

### Chat Interface
- **D-07:** Chat lives in a **fixed bottom panel** — collapsed to a bar when idle, expands to ~300px when clicked. Dashboard content remains fully visible above it. No separate page, no sidebar.
- **D-08:** Anti-hallucination: **inject the full briefing JSON as the Claude system context**. Prompt pattern: "You are a personal investing analyst. Only use the following data: {briefing_json}. Do not invent facts or cite sources not in the data." Simple and reliable for MVP.
- **D-09:** Chat history is **in-memory only** — resets on page reload. No SQLite persistence for MVP. Each session starts fresh (daily briefing rhythm means yesterday's questions are stale anyway).

### News Organisation
- **D-10:** One **News card with four tabs**: "My Holdings | India Macro | Germany/EU Macro | US Macro". Single contained card, no duplication across sections.
- **D-11:** Show **3–5 headlines per tab** — top items by NewsAPI relevance score. Enough to cover the day's main stories without overload.
- **D-12:** Each headline shows: **clickable headline text + source name + time ago** (e.g. "Reliance beats Q4 — Reuters, 3h ago"). No summary needed for MVP.
- **D-13:** Holdings tab aggregates news across all holdings (not per-holding inline). The expanded row does NOT include news — signals and AI narrative only.

### Locked Architecture (carry-forward from Phase 1)
- Claude Haiku 4.5 for AI synthesis
- pandas-ta for RSI, MACD, SMA50, SMA200
- NewsAPI (100 req/day) for holdings + macro news; Finnhub for analyst ratings + price targets
- yfinance for historical OHLCV data (needed for indicator computation)
- BriefingOrchestrator.generate() is the integration point — Phase 2 adds news, signals, analyst, and AI synthesis steps to that pipeline
- Briefing stored as JSON snapshot in briefing_snapshots — Phase 2 enriches the snapshot schema

### Claude's Discretion
- Exact prompt wording for AI synthesis (keep instructions tight, financial-domain-appropriate)
- Whether to batch Finnhub analyst calls or fetch per-holding (rate limit: 60 req/min)
- Exact NewsAPI query strategy for macro themes (suggested: "India economy OR RBI OR Nifty", etc.)
- How to handle holdings with no news (show "No recent news" state, not empty tab)
- How to handle holdings with no analyst coverage on Finnhub (show "No analyst data" gracefully)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 Foundation
- `.planning/phases/01-core-daily-briefing/01-VERIFICATION.md` — 16/16 must-haves verified; confirms what Phase 1 actually delivered
- `backend/core/briefing.py` — BriefingOrchestrator.generate() is the integration point for Phase 2 pipeline steps
- `backend/core/data_fetcher.py` — DataFetcher class; Phase 2 adds fetch_news(), fetch_signals(), fetch_analyst() methods here
- `backend/models.py` — Pydantic models; Phase 2 extends HoldingResponse and BriefingSnapshot schema

### Requirements
- `.planning/REQUIREMENTS.md` — Phase 2 requirements: MKT-04, MKT-05, MKT-06, MKT-07, SIG-01, SIG-02, SIG-03, SIG-04, BRIEF-04, BRIEF-05, FX-04
- `.planning/ROADMAP.md` §"Phase 2: Intelligence & Chat" — success criteria and phase boundary

### Frontend
- `frontend/src/components/PortfolioTable.jsx` — table to be extended with Rec badge column and expandable rows
- `frontend/src/Dashboard.jsx` — layout entry point; chat panel and News card to be added here

### Tech Stack (already in use)
- pandas-ta docs: https://github.com/twopirllc/pandas-ta — RSI, MACD, SMA already in CLAUDE.md stack
- Finnhub Python: `finnhub-python` package — ratings + price targets endpoint
- NewsAPI Python: `newsapi-python` package — everything endpoint filtered by company name or macro keywords

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BriefingOrchestrator.generate()` — sequential fetch pipeline; Phase 2 adds steps 4 (signals), 5 (news), 6 (analyst), 7 (AI synthesis) before the final assemble step
- `DataFetcher` class — already handles yfinance + SQLite caching patterns; extend with news/analyst methods using the same try/except + cache pattern
- `HoldingResponse` model — already has ticker, name, region, broker, P&L fields; extend with `rec`, `rsi`, `macd`, `sma50`, `sma200`, `analyst_rating`, `analyst_target`, `ai_narrative` fields
- `PortfolioTable.jsx` — React table component; expandable row pattern to be added (currently flat rows)
- `IndicesCard.jsx`, `FXCard.jsx` — card component pattern to follow for new NewsCard

### Established Patterns
- **Try/except per data source**: each fetch step in BriefingOrchestrator is wrapped independently — partial data OK, errors logged. Phase 2 must follow the same pattern (news failure ≠ signals failure)
- **SQLite caching**: price and FX data cached to DB. News should be cached too (avoid re-fetching same articles within same day)
- **JSON snapshot**: briefing stored as complete JSON blob. Phase 2 enriches this blob — downstream GET /api/briefing returns the enriched version
- **Parameterized SQL**: all DB writes use `?` placeholders — maintain this in new news/signals tables

### Integration Points
- `BriefingOrchestrator.generate()` — add news/signals/analyst/AI steps here
- `backend/database.py` — add `news_cache` and `signals_cache` tables for Phase 2 caching
- `GET /api/briefing` — already returns enriched snapshot; Phase 2 data flows through this same endpoint (no new endpoints needed for basic display)
- `POST /api/chat` — new endpoint; receives user message + current briefing context, returns Claude response
- `frontend/src/Dashboard.jsx` — add NewsCard and ChatPanel components alongside existing cards

</code_context>

<specifics>
## Specific Ideas

- Chat panel should feel like a "briefing assistant" — not a generic chatbot. Opening message: "Ask me anything about today's briefing." The system prompt positions Claude as a personal analyst with access only to today's data.
- The Rec badge should use the same green/red palette already established by P&L colouring in Phase 1 (green = positive = BUY, red = negative = SELL, grey = neutral = HOLD).
- News tabs default to "My Holdings" on open — most relevant to the user's specific portfolio.
- If a holding has no OHLCV history (e.g. recently imported, or yfinance data gap), skip signal computation for that holding and show "Signals unavailable" in the expanded row.

</specifics>

<deferred>
## Deferred Ideas

- Per-holding news inline in the expanded row — decided against (D-13); keeps expanded row focused on signals + AI only
- SQLite chat history persistence — deferred to v2; in-memory is sufficient for MVP daily rhythm
- Heat map / benchmark comparison — already out of scope in ROADMAP (Phase 3 Polish, deferred)
- Cash deployment suggestions (FX-04) — in scope per REQUIREMENTS.md but not discussed; planner should include it. Suggested: if idle cash > X EUR or INR, include a suggestion in the AI briefing section based on market conditions.

</deferred>

---

*Phase: 02-intelligence-chat*
*Context gathered: 2026-05-16*
