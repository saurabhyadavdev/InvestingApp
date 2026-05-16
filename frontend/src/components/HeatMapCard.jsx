import React, { useMemo } from 'react';

/**
 * HeatMapCard
 * Displays portfolio holdings as proportional color-coded tiles,
 * sized by position market value and colored by daily % change.
 */

/**
 * Return a background color for a heat map tile based on daily % change.
 * @param {number|null} dailyPct
 * @returns {string} hex color
 */
function getTileColor(dailyPct) {
  if (dailyPct == null) return '#F5F5F5';  // neutral gray — no data
  if (dailyPct >= 3)   return '#E8F5E9';   // strong green
  if (dailyPct >= 0)   return '#F1FBF2';   // mild green
  if (dailyPct >= -3)  return '#FFF3F4';   // mild red
  return '#FFEBEE';                         // strong red
}

/**
 * HeatMapCard component.
 *
 * Props:
 *   holdings {Array}  - Array of holding objects from the briefing portfolio.
 *   fxRate   {number} - EUR/INR FX rate for value normalization (default 90).
 */
export default function HeatMapCard({ holdings, fxRate = 90 }) {
  const { tiles, totalValue } = useMemo(() => {
    if (!holdings || holdings.length === 0) {
      return { tiles: [], totalValue: 0 };
    }

    const filtered = holdings.filter(
      (h) =>
        h.asset_type !== 'cash' &&
        h.current_price != null &&
        h.quantity > 0
    );

    let total = 0;
    const mapped = filtered.map((h) => {
      const valueInr =
        h.currency === 'EUR'
          ? h.current_price * h.quantity * fxRate
          : h.current_price * h.quantity;
      total += valueInr;
      return { ...h, valueInr };
    });

    return { tiles: mapped, totalValue: total };
  }, [holdings, fxRate]);

  if (tiles.length === 0) {
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
          marginBottom: 16,
          marginTop: 0,
          color: 'var(--color-text-primary)',
        }}
      >
        Portfolio Heat Map
      </h2>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {tiles.map((t) => {
          const pctOfTotal =
            totalValue > 0 ? (t.valueInr / totalValue) * 100 : 0;

          const currencySymbol =
            t.currency === 'EUR' ? '€' : t.currency === 'USD' ? '$' : '₹';

          const titleText = `${t.name || t.ticker} — ${currencySymbol}${t.current_price}`;

          const dailyLabel =
            t.daily_pct != null
              ? (t.daily_pct >= 0 ? '+' : '') +
                t.daily_pct.toFixed(2) +
                '%'
              : '—';

          return (
            <div
              key={t.id ?? t.ticker}
              title={titleText}
              style={{
                flex: '0 0 auto',
                width: `calc(${pctOfTotal.toFixed(1)}% - 4px)`,
                minWidth: 80,
                minHeight: 60,
                background: getTileColor(t.daily_pct),
                borderRadius: 4,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '8px 6px',
                cursor: 'default',
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: 'var(--color-text-primary)',
                  textAlign: 'center',
                }}
              >
                {t.ticker}
              </span>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color:
                    t.daily_pct == null
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
    </section>
  );
}
