import React, { useMemo } from 'react';

const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{10}$/;

/** Return a short display label for a holding tile. */
function getDisplayLabel(holding) {
  if (ISIN_RE.test(holding.ticker)) {
    // ISIN stored as ticker — prefer name (first word or first 10 chars)
    if (holding.name) {
      const firstWord = holding.name.split(/[\s,/-]/)[0];
      return firstWord.length <= 10 ? firstWord : firstWord.slice(0, 9) + '…';
    }
    return holding.ticker.slice(0, 6);
  }
  return holding.ticker;
}

/**
 * HeatMapCard
 * Displays portfolio holdings as proportional color-coded tiles, grouped by
 * market (India / US / Germany / Other), sized by position value within their
 * group and colored by daily % change.
 */

/**
 * Build a tile's visual style from its daily % change — a vivid gradient fill
 * plus a glow whose intensity scales with the size of the move.
 * @param {number|null} dailyPct
 * @returns {{background: string, boxShadow: string, border: string}}
 */
function getTileStyle(dailyPct) {
  if (dailyPct == null) {
    return {
      background: 'linear-gradient(145deg, #2A2D3E, #20232f)',
      boxShadow: 'none',
      border: '1px solid #33384d',
    };
  }
  const up = dailyPct >= 0;
  const mag = Math.min(Math.abs(dailyPct), 5) / 5; // 0..1 intensity
  const alpha = (0.18 + mag * 0.55).toFixed(2);
  const glow = (0.15 + mag * 0.45).toFixed(2);
  const rgb = up ? '74, 222, 128' : '248, 113, 113';
  return {
    background: `linear-gradient(150deg, rgba(${rgb}, ${alpha}), rgba(${rgb}, ${(alpha * 0.35).toFixed(2)}))`,
    boxShadow: `inset 0 0 0 1px rgba(${rgb}, ${(mag * 0.5 + 0.2).toFixed(2)}), 0 0 ${(mag * 14 + 2).toFixed(0)}px rgba(${rgb}, ${glow})`,
    border: 'none',
  };
}

// Map a holding's region to a heat-map market group. etf/nordic/unknown and
// any unrecognized region collapse into a single "Other" bucket.
function getMarketGroup(region) {
  if (region === 'india') return 'india';
  if (region === 'us') return 'us';
  if (region === 'germany') return 'germany';
  return 'other';
}

// Render order + display metadata for the market groups.
const MARKET_GROUPS = [
  { key: 'india', label: 'India', flag: '🇮🇳', accent: '#FF9933' },
  { key: 'us', label: 'US Markets', flag: '🇺🇸', accent: '#4D9EFF' },
  { key: 'germany', label: 'Germany', flag: '🇩🇪', accent: '#FFCC00' },
  { key: 'other', label: 'ETFs & Other', flag: '🌐', accent: '#94A3B8' },
];

/**
 * HeatMapCard component.
 *
 * Props:
 *   holdings {Array}  - Array of holding objects from the briefing portfolio.
 *   fxRate   {number} - EUR/INR FX rate for value normalization (default 90).
 */
export default function HeatMapCard({ holdings, fxRate = 90, refreshing = false }) {
  const groups = useMemo(() => {
    if (!holdings || holdings.length === 0) {
      return [];
    }

    const filtered = holdings.filter(
      (h) =>
        h.asset_type !== 'cash' &&
        h.current_price != null &&
        h.quantity > 0
    );

    // Deduplicate: same stock may appear in multiple brokers (same ISIN/ticker_yfinance).
    // Merge by ticker_yfinance → isin → ticker, summing quantities.
    const seen = new Map();
    for (const h of filtered) {
      const key = h.ticker_yfinance || h.isin || h.ticker;
      if (!seen.has(key)) {
        seen.set(key, { ...h });
      } else {
        const existing = seen.get(key);
        existing.quantity = (existing.quantity || 0) + (h.quantity || 0);
        if (existing.current_price == null) existing.current_price = h.current_price;
        if (existing.daily_pct == null) existing.daily_pct = h.daily_pct;
      }
    }
    const deduped = Array.from(seen.values());

    const mapped = deduped.map((h) => {
      const valueInr =
        h.currency === 'EUR'
          ? h.current_price * h.quantity * fxRate
          : h.current_price * h.quantity;
      return { ...h, valueInr, _group: getMarketGroup(h.region) };
    });

    // Bucket tiles by market group, sizing each tile relative to its own
    // group's total so every market section fills its own row.
    return MARKET_GROUPS.map((meta) => {
      const tiles = mapped.filter((t) => t._group === meta.key);
      const groupTotal = tiles.reduce((sum, t) => sum + t.valueInr, 0);

      // Value-weighted net daily change for the group's header pill.
      let weighted = 0;
      let weightedBase = 0;
      for (const t of tiles) {
        if (t.daily_pct != null) {
          weighted += t.daily_pct * t.valueInr;
          weightedBase += t.valueInr;
        }
      }
      const netPct = weightedBase > 0 ? weighted / weightedBase : null;

      // Sort: most loss first → most gain last (nulls go to the middle)
      tiles.sort((a, b) => (a.daily_pct ?? 0) - (b.daily_pct ?? 0));

      return { ...meta, tiles, groupTotal, netPct };
    }).filter((g) => g.tiles.length > 0);
  }, [holdings, fxRate]);

  if (groups.length === 0) {
    return (
      <section
        style={{
          background: 'var(--color-bg-card)',
          border: '1px solid var(--color-border)',
          borderRadius: 8,
          padding: '20px 24px',
        }}
      >
        <h2
          style={{
            fontSize: 20,
            fontWeight: 600,
            marginBottom: 16,
            marginTop: 0,
            color: 'var(--color-text-primary)',
          }}
        >
          Portfolio Heat Map
        </h2>
        <p
          style={{
            color: 'var(--color-text-secondary)',
            fontSize: 14,
            margin: 0,
          }}
        >
          No holdings to display heat map.
        </p>
      </section>
    );
  }

  return (
    <section
      style={{
        background: 'var(--color-bg-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        padding: '20px 24px',
      }}
    >
      <h2
        style={{
          fontSize: 20,
          fontWeight: 600,
          marginBottom: 18,
          marginTop: 0,
          color: 'var(--color-text-primary)',
        }}
      >
        Portfolio Heat Map
      </h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 16,
        }}
      >
        {groups.map((group) => {
          const showNet = !refreshing && group.netPct != null;
          const netUp = (group.netPct ?? 0) >= 0;
          return (
            <div
              key={group.key}
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--color-border)',
                borderRadius: 10,
                padding: 12,
              }}
            >
              {/* Group header chip */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 10,
                  paddingBottom: 8,
                  borderBottom: `2px solid ${group.accent}`,
                }}
              >
                <span style={{ fontSize: 16, lineHeight: 1 }}>{group.flag}</span>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 700,
                    letterSpacing: '0.03em',
                    color: 'var(--color-text-primary)',
                    flex: 1,
                  }}
                >
                  {group.label}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {group.tiles.length}
                </span>
                {showNet && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '2px 7px',
                      borderRadius: 999,
                      color: netUp ? 'var(--color-positive)' : 'var(--color-negative)',
                      background: netUp
                        ? 'rgba(74, 222, 128, 0.12)'
                        : 'rgba(248, 113, 113, 0.12)',
                    }}
                  >
                    {(netUp ? '+' : '') + group.netPct.toFixed(2)}%
                  </span>
                )}
              </div>

              {/* Tiles */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                {group.tiles.map((t) => {
                  const pctOfGroup =
                    group.groupTotal > 0 ? (t.valueInr / group.groupTotal) * 100 : 0;

                  const currencySymbol =
                    t.currency === 'EUR' ? '€' : t.currency === 'USD' ? '$' : '₹';

                  const titleText = `${t.name || t.ticker} — ${currencySymbol}${t.current_price}`;

                  // While a price refresh is in flight the cached daily_pct is
                  // stale — show a neutral "updating…" placeholder.
                  const showPct = !refreshing && t.daily_pct != null;

                  const dailyLabel = refreshing
                    ? '…'
                    : t.daily_pct != null
                    ? (t.daily_pct >= 0 ? '+' : '') + t.daily_pct.toFixed(2) + '%'
                    : '—';

                  const tileStyle = getTileStyle(showPct ? t.daily_pct : null);

                  return (
                    <div
                      key={t.id ?? t.ticker}
                      title={titleText}
                      style={{
                        flex: '0 0 auto',
                        width: `calc(${Math.max(pctOfGroup, 18).toFixed(1)}% - 3px)`,
                        minWidth: 64,
                        minHeight: 48,
                        borderRadius: 6,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '6px 4px',
                        cursor: 'default',
                        ...tileStyle,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: 'var(--color-text-primary)',
                          textAlign: 'center',
                          lineHeight: 1.1,
                        }}
                      >
                        {getDisplayLabel(t)}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          marginTop: 2,
                          color: !showPct
                            ? 'var(--color-text-secondary)'
                            : t.daily_pct >= 0
                            ? 'var(--color-positive)'
                            : 'var(--color-negative)',
                          textAlign: 'center',
                        }}
                      >
                        {dailyLabel}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
