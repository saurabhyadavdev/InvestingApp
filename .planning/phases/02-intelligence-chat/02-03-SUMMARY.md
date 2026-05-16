---
phase: 02-intelligence-chat
plan: 03
subsystem: ui
tags: [react, jsx, css, portfolio-table, news-card, chat-panel]

# Dependency graph
requires:
  - phase: 01-portfolio-foundation
    provides: PortfolioTable base component with holdings data shape

provides:
  - PortfolioTable with Rec badge column and expandable signal row (RSI/MACD/SMA/analyst/AI narrative)
  - NewsCard component with 4-tab news interface (holdings/india/germany/us)
  - Dashboard Market Intelligence section wired to NewsCard
  - ChatPanel collapsed-bar placeholder at fixed bottom

affects:
  - 02-02 (backend pipeline that populates h.rec, h.rsi_14, h.macd, etc.)
  - 02-04 (chat panel — will replace the placeholder div created here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "React.Fragment wrapper around holding row + expandable row to avoid invalid DOM nesting in tbody"
    - "REC_STYLES lookup object: unknown values render no badge (falsy guard prevents injection)"
    - "NewsCard reads from briefing?.news with empty-object fallback — component safe when briefing is null"

key-files:
  created:
    - frontend/src/components/NewsCard.jsx
  modified:
    - frontend/src/components/PortfolioTable.jsx
    - frontend/src/index.css
    - frontend/src/Dashboard.jsx

key-decisions:
  - "Used React.Fragment to wrap holding row + expanded row pair to avoid invalid <tr> nesting in tbody"
  - "REC_STYLES lookup approach: only known keys (BUY/HOLD/SELL) render a badge; no dynamic class injection"
  - "ChatPanel is a static placeholder div; full implementation deferred to Plan 04"

patterns-established:
  - "Expandable table row pattern: React.Fragment key on outer fragment, expandedId state toggled by row onClick"
  - "NewsCard tab pattern: activeTab state, tabs/tabLabels/emptyMessages config objects for maintainability"

requirements-completed:
  - SIG-01
  - MKT-04
  - MKT-05
  - MKT-06
  - MKT-07

# Metrics
duration: 2min
completed: 2026-05-16
---

# Phase 2 Plan 03: Frontend Signals & News UI Summary

**PortfolioTable gains colour-coded Rec badges and expandable signal rows (RSI/MACD/SMA/analyst/AI narrative); new NewsCard delivers 4-tab news interface; Dashboard wired with Market Intelligence section and fixed ChatPanel placeholder**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-16T09:22:16Z
- **Completed:** 2026-05-16T09:23:58Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- PortfolioTable extended with Rec badge column (BUY green / HOLD grey / SELL red) and clickable expandable rows showing all Phase 2 signal fields with null-safe fallbacks
- NewsCard component created with 4-tab interface defaulting to "My Holdings"; each tab shows article list or empty-state; all external links secured with `rel="noopener noreferrer"`
- Dashboard updated: Market Intelligence section inserted after EUR/INR, fixed-bottom ChatPanel placeholder bar renders at 44px height

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend PortfolioTable with Rec badge column and expandable signal row** - `f7f133c` (feat)
2. **Task 2: Create NewsCard component and wire into Dashboard** - `78f9e3e` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/components/PortfolioTable.jsx` - Added useState, REC_STYLES, expandedId toggle, Rec/chevron columns (total 11), expandable signal row, tfoot colSpan updated from 9 to 11
- `frontend/src/index.css` - Appended .expanded-row, .signals-panel, .signals-row, .ai-narrative CSS classes
- `frontend/src/components/NewsCard.jsx` - New file: 4-tab news card reading briefing.news with empty states per tab
- `frontend/src/Dashboard.jsx` - Added NewsCard import, Market Intelligence section, ChatPanel placeholder, paddingBottom on page container

## Decisions Made
- Used `React.Fragment` to wrap the holding `<tr>` and expanded `<tr>` pair — required to avoid invalid DOM structure inside `<tbody>` (rows must be direct children)
- REC_STYLES lookup prevents any dynamic style injection: unknown h.rec values skip the badge entirely via the `h.rec &&` guard
- ChatPanel is a pure placeholder div; no state or event handling; Plan 04 replaces it entirely

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- UI is fully ready to display Phase 2 data: when Plan 02's backend pipeline starts populating `h.rec`, `h.rsi_14`, `h.macd`, etc., the table will immediately show badges and signal data
- NewsCard will display articles as soon as `briefing.news` is populated by the backend
- ChatPanel placeholder is in place for Plan 04's full chat implementation

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All external URLs in NewsCard articles open via standard `<a target="_blank" rel="noopener noreferrer">` — T-02-10 mitigation applied as specified.

---
*Phase: 02-intelligence-chat*
*Completed: 2026-05-16*
