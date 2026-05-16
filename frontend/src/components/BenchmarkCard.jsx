/**
 * BenchmarkCard — Compare portfolio returns vs Nifty 50, S&P 500, and DAX.
 *
 * Props:
 *   benchmarkData: object from briefing.benchmark_data
 *     {
 *       windows: string[],
 *       portfolio: {1M, 3M, YTD, 1Y},
 *       indices: {"^NSEI": {1M,...}, "^GSPC": {1M,...}, "^GDAXI": {1M,...}},
 *       regional: {india: {1M,...}, germany_us_etf: {1M,...}}
 *     }
 *
 * Renders a period switcher (1M, 3M, YTD, 1Y) and a comparison table.
 * Cells are color-coded: green when portfolio beats the index, red when it lags.
 * Regional breakdown rows show India vs Nifty 50 and Germany/US/ETF vs S&P 500 / DAX.
 */
import React, { useState } from 'react';

const WINDOWS = ['1M', '3M', 'YTD', '1Y'];

const INDEX_LABELS = {
  '^NSEI':  'Nifty 50',
  '^GSPC':  'S&P 500',
  '^GDAXI': 'DAX',
};

/** Format a return percentage for display. */
function formatPct(pct) {
  if (pct == null) return '—';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

/**
 * BenchmarkCell — renders a single return cell with optional beat/lag color coding.
 *
 * Props:
 *   pct          float|null  — the value to display (portfolio or index return)
 *   benchmarkPct float|null  — the index return to compare against (null = no comparison)
 */
function BenchmarkCell({ pct, benchmarkPct }) {
  if (pct == null) {
    return (
      <td
        style={{
          color: 'var(--color-text-secondary)',
          textAlign: 'right',
          padding: '8px',
          fontFamily: 'monospace',
        }}
      >
        —
      </td>
    );
  }

  // Determine color: green if beats benchmark, red if lags, primary if no benchmark
  const beat = benchmarkPct == null ? null : pct >= benchmarkPct;
  let color;
  if (beat === true) {
    color = 'var(--color-positive)';
  } else if (beat === false) {
    color = 'var(--color-negative)';
  } else {
    color = 'var(--color-text-primary)';
  }

  return (
    <td
      style={{
        color,
        fontWeight: 600,
        fontFamily: 'monospace',
        textAlign: 'right',
        padding: '8px',
      }}
    >
      {formatPct(pct)}
    </td>
  );
}

/** Common <th> cell style. */
function headerStyle(align = 'right') {
  return {
    textAlign: align,
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
    padding: '4px 8px',
    borderBottom: '1px solid var(--color-border)',
    background: 'var(--color-bg-card)',
  };
}

/** Common <td> label style (left-aligned window label). */
function labelCellStyle(bold = false) {
  return {
    padding: '8px',
    fontSize: 14,
    fontWeight: bold ? 700 : 400,
    color: 'var(--color-text-primary)',
    borderBottom: '1px solid var(--color-border)',
    whiteSpace: 'nowrap',
  };
}

/** Empty dash <td>. */
function DashCell() {
  return (
    <td
      style={{
        color: 'var(--color-text-secondary)',
        textAlign: 'right',
        padding: '8px',
        fontFamily: 'monospace',
        borderBottom: '1px solid var(--color-border)',
      }}
    >
      —
    </td>
  );
}

export default function BenchmarkCard({ benchmarkData }) {
  const [activePeriod, setActivePeriod] = useState('1M');

  // Empty / loading guard
  const isEmpty =
    !benchmarkData || Object.keys(benchmarkData).length === 0 || !benchmarkData.portfolio;

  if (isEmpty) {
    return (
      <section
        style={{
          background: 'var(--color-bg-card)',
          borderRadius: 8,
          padding: '20px 24px',
          border: '1px solid var(--color-border)',
        }}
      >
        <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16, color: 'var(--color-text-primary)' }}>
          Benchmark Comparison
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 14, margin: 0 }}>
          Benchmark data unavailable. Check data fetcher logs.
        </p>
      </section>
    );
  }

  const {
    windows = WINDOWS,
    portfolio = {},
    indices = {},
    regional = {},
  } = benchmarkData;

  const nifty  = indices['^NSEI']  || {};
  const sp500  = indices['^GSPC']  || {};
  const dax    = indices['^GDAXI'] || {};
  const india  = regional.india          || {};
  const intl   = regional.germany_us_etf || {};

  const w = activePeriod;

  return (
    <section
      style={{
        background: 'var(--color-bg-card)',
        borderRadius: 8,
        padding: '20px 24px',
        border: '1px solid var(--color-border)',
      }}
    >
      {/* Card title */}
      <h2
        style={{
          fontSize: 20,
          fontWeight: 600,
          marginBottom: 16,
          marginTop: 0,
          color: 'var(--color-text-primary)',
        }}
      >
        Benchmark Comparison
      </h2>

      {/* Period switcher */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {windows.map((period) => {
          const isActive = period === activePeriod;
          return (
            <button
              key={period}
              onClick={() => setActivePeriod(period)}
              style={{
                padding: '4px 12px',
                fontSize: 13,
                fontWeight: isActive ? 700 : 400,
                cursor: 'pointer',
                border: '1px solid var(--color-border)',
                borderRadius: 4,
                background: isActive ? '#1565C0' : 'var(--color-bg-card)',
                color: isActive ? '#ffffff' : 'var(--color-text-primary)',
              }}
            >
              {period}
            </button>
          );
        })}
      </div>

      {/* Main comparison table: rows = windows, columns = metrics */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 8 }}>
        <thead>
          <tr>
            <th style={headerStyle('left')}>Period</th>
            <th style={headerStyle()}>My Portfolio</th>
            <th style={headerStyle()}>{INDEX_LABELS['^NSEI']}</th>
            <th style={headerStyle()}>{INDEX_LABELS['^GSPC']}</th>
            <th style={headerStyle()}>{INDEX_LABELS['^GDAXI']}</th>
          </tr>
        </thead>
        <tbody>
          {windows.map((period) => (
            <tr
              key={period}
              style={{
                background: period === activePeriod ? 'rgba(21,101,192,0.05)' : undefined,
              }}
            >
              <td
                style={{
                  ...labelCellStyle(true),
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                {period}
              </td>
              {/* My Portfolio — no benchmark comparison for the total column */}
              <BenchmarkCell pct={portfolio[period]} benchmarkPct={null} />
              {/* vs Nifty 50 */}
              <BenchmarkCell pct={portfolio[period]} benchmarkPct={nifty[period] ?? null} />
              {/* vs S&P 500 */}
              <BenchmarkCell pct={portfolio[period]} benchmarkPct={sp500[period] ?? null} />
              {/* vs DAX */}
              <BenchmarkCell pct={portfolio[period]} benchmarkPct={dax[period] ?? null} />
            </tr>
          ))}
        </tbody>
      </table>

      {/* Regional breakdown sub-heading */}
      <h3
        style={{
          fontSize: 15,
          fontWeight: 600,
          marginTop: 16,
          marginBottom: 8,
          color: 'var(--color-text-primary)',
        }}
      >
        Regional Breakdown
      </h3>

      {/* Regional table — same column layout */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={headerStyle('left')}>Bucket / Period</th>
            <th style={headerStyle()}>Return</th>
            <th style={headerStyle()}>{INDEX_LABELS['^NSEI']}</th>
            <th style={headerStyle()}>{INDEX_LABELS['^GSPC']}</th>
            <th style={headerStyle()}>{INDEX_LABELS['^GDAXI']}</th>
          </tr>
        </thead>
        <tbody>
          {/* India Holdings vs Nifty 50 */}
          {windows.map((period) => (
            <tr key={`india-${period}`}>
              <td style={{ ...labelCellStyle(), borderBottom: '1px solid var(--color-border)' }}>
                India {period}
              </td>
              {/* Raw India return (no benchmark col) */}
              <BenchmarkCell pct={india[period] ?? null} benchmarkPct={null} />
              {/* India vs Nifty 50 */}
              <BenchmarkCell pct={india[period] ?? null} benchmarkPct={nifty[period] ?? null} />
              {/* India vs S&P 500 — not meaningful, show dash */}
              <DashCell />
              {/* India vs DAX — not meaningful, show dash */}
              <DashCell />
            </tr>
          ))}

          {/* Germany/US/ETF vs S&P 500 and DAX */}
          {windows.map((period) => (
            <tr key={`intl-${period}`}>
              <td style={{ ...labelCellStyle(), borderBottom: '1px solid var(--color-border)' }}>
                Intl {period}
              </td>
              {/* Raw international return */}
              <BenchmarkCell pct={intl[period] ?? null} benchmarkPct={null} />
              {/* Intl vs Nifty — not meaningful, show dash */}
              <DashCell />
              {/* Intl vs S&P 500 */}
              <BenchmarkCell pct={intl[period] ?? null} benchmarkPct={sp500[period] ?? null} />
              {/* Intl vs DAX */}
              <BenchmarkCell pct={intl[period] ?? null} benchmarkPct={dax[period] ?? null} />
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
