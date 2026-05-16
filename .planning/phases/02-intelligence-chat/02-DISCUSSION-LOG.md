# Phase 2: Intelligence & Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 02-intelligence-chat
**Areas discussed:** Signal display, AI synthesis placement, Chat interface, News organisation

---

## Signal Display

| Option | Description | Selected |
|--------|-------------|----------|
| Expand the portfolio table | Add RSI/MACD/MA columns to existing table — compact, wide | ✓ |
| Signals section below portfolio | Separate card below table — cleaner separation | |
| Expandable row per holding | Click row to expand in-place — no new sections | |

**User's choice:** Expand the portfolio table (Rec badge column)
**Notes:** Badge only in main table; signal numbers inside expanded row only. Table stays clean.

| Option | Description | Selected |
|--------|-------------|----------|
| Colour-coded badge | Green BUY / grey HOLD / red SELL pill in new column | ✓ |
| Text + colour in signal columns | RSI/MACD/Rec as coloured text columns | |

**User's choice:** Colour-coded badge

| Option | Description | Selected |
|--------|-------------|----------|
| Only in expanded row | Clean table; expand to see RSI/MACD/MAs | ✓ |
| Add RSI column to main table | RSI always visible alongside P&L | |

**User's choice:** Signal numbers only in expanded row

---

## AI Synthesis Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Inside the expanded row | Below signal numbers when row is expanded | ✓ |
| Separate Briefing Intelligence section | New card below portfolio table | |
| Both — short summary + full section | One-liner in row, paragraph in section | |

**User's choice:** Inside the expanded row

| Option | Description | Selected |
|--------|-------------|----------|
| 2–3 sentences | Scannable, actionable, fits in expanded row | ✓ |
| One-liner only | Fastest; loses reasoning chain | |
| Full paragraph (5–8 sentences) | Deep; too much for daily rhythm | |

**User's choice:** 2–3 sentences

| Option | Description | Selected |
|--------|-------------|----------|
| All holdings at briefing time | Pre-generated; ~$0.01–0.03 extra Haiku cost | ✓ |
| On-demand per holding | Zero cost if not expanded; 300–800ms wait | |

**User's choice:** All holdings at briefing generation time

---

## Chat Interface

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed bottom panel | Collapsed bar → expands to 300px; dashboard stays visible | ✓ |
| Sidebar panel | Collapsible right panel; dashboard narrows | |
| Separate /chat page | Clean separation; loses briefing context visually | |

**User's choice:** Fixed bottom panel

| Option | Description | Selected |
|--------|-------------|----------|
| Inject full briefing as system context | Serialize briefing JSON into Claude system prompt | ✓ |
| Tool-use pattern | Claude given tools to fetch specific data | |

**User's choice:** Full briefing JSON injected as system context

| Option | Description | Selected |
|--------|-------------|----------|
| Reset on reload (MVP) | In-memory; clean slate each session | ✓ |
| Persist to SQLite | Store in chat_messages table; scroll history | |

**User's choice:** Reset on reload

---

## News Organisation

| Option | Description | Selected |
|--------|-------------|----------|
| One News card with tabs | Four tabs: My Holdings / India / Germany-EU / US Macro | ✓ |
| Holdings news inline per holding | News inside expanded row alongside signals | |
| Two sections: Holdings + Macro | Holdings card + macro card | |

**User's choice:** One News card with tabs (default tab: My Holdings)

| Option | Description | Selected |
|--------|-------------|----------|
| 3–5 per tab | Top by relevance score | ✓ |
| Top 1–2 only | Ultra-brief | |
| Up to 10 per tab | Comprehensive but overwhelming | |

**User's choice:** 3–5 headlines per tab

| Option | Description | Selected |
|--------|-------------|----------|
| Headline + source + time ago | e.g. "Reliance beats Q4 — Reuters, 3h ago" | ✓ |
| Headline + 1-sentence summary | More context; taller cards | |

**User's choice:** Headline + source + time ago

---

## Claude's Discretion

- Exact prompt wording for AI synthesis (financial-domain tone)
- Whether to batch or serial-fetch Finnhub analyst calls (60 req/min limit)
- NewsAPI query strings for macro themes
- Empty-state handling: no news, no analyst coverage, no signal data
- Cash deployment suggestions (FX-04) — in scope but not discussed; planner to include

## Deferred Ideas

- Per-holding news inline in expanded row — decided against; keeps expanded row focused
- SQLite chat history persistence — deferred to v2
- Heat map / benchmark comparison — already out of scope (Phase 3 Polish)
