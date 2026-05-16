import React, { useState } from 'react';

/**
 * PortfolioTable
 * Dense table showing all holdings with P&L per UI-SPEC.
 * P&L cells colored: positive=green, negative=red, zero=neutral gray.
 * Phase 2: Rec badge column + expandable signal row (RSI, MACD, SMA, analyst, AI narrative).
 */

function getCurrencySymbol(currency) {
  if (currency === 'EUR') return '€';
  if (currency === 'INR') return '₹';
  if (currency === 'USD') return '$';
  return currency;
}

// CSS classes map to CSS variables: pl-positive → var(--color-positive), pl-negative → var(--color-negative)
function getPLClass(value) {
  if (value > 0) return 'pl-positive'; // var(--color-positive) #28A745
  if (value < 0) return 'pl-negative'; // var(--color-negative) #DC3545
  return 'pl-zero'; // var(--color-neutral)
}

function formatNum(value, decimals = 2) {
  if (value === null || value === undefined) return '—';
  return Number(value).toFixed(decimals);
}

const REC_STYLES = {
  BUY:  { background: '#28A745', color: '#fff' },
  SELL: { background: '#DC3545', color: '#fff' },
  HOLD: { background: '#6C757D', color: '#fff' },
};

export default function PortfolioTable({ holdings, totalInr, totalEur, totalUsd = 0, fxRate = 90, alertTickers }) {
  // Normalise alertTickers to a Set for O(1) lookup
  const _alertSet = alertTickers instanceof Set
    ? alertTickers
    : new Set(alertTickers || []);
  const [expandedId, setExpandedId] = useState(null);

  if (!holdings || holdings.length === 0) {
    return (
      <div className="empty-state" id="import-anchor">
        <h2>No portfolio data yet</h2>
        <p>
          Import your Zerodha or Trade Republic CSV to see holdings, P&L, and allocation breakdown.
        </p>
        <button
          className="btn-import"
          onClick={() => {
            const el = document.querySelector('.import-csv-section');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
          }}
        >
          Import Portfolio
        </button>
      </div>
    );
  }

  // Compute sums for summary row
  const totalPlInr = holdings.reduce((sum, h) => {
    if (h.currency === 'EUR') return sum + (h.pl || 0) * fxRate;
    return sum + (h.pl || 0);
  }, 0);
  const totalPlEur = holdings.reduce((sum, h) => {
    if (h.currency === 'INR') return sum + (h.pl || 0) / fxRate;
    return sum + (h.pl || 0);
  }, 0);

  return (
    <div className="portfolio-table-wrapper">
      <table className="portfolio-table">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Qty</th>
            <th>Avg Buy</th>
            <th>Current</th>
            <th>P&amp;L (INR)</th>
            <th>P&amp;L %</th>
            <th>Currency</th>
            <th>Region</th>
            <th>Broker</th>
            <th>Rec</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, idx) => {
            const sym = getCurrencySymbol(h.currency);
            const plInr = h.currency === 'EUR'
              ? (h.pl || 0) * fxRate
              : (h.pl || 0);
            const rowKey = h.id || `${h.broker}-${h.ticker}-${idx}`;
            return (
              <React.Fragment key={rowKey}>
                <tr
                  onClick={() => setExpandedId(expandedId === h.id ? null : h.id)}
                  style={{
                    cursor: 'pointer',
                    background: (_alertSet.has(h.ticker_yfinance) || _alertSet.has(h.ticker))
                      ? 'rgba(255, 193, 7, 0.12)'
                      : undefined,
                  }}
                >
                  <td>{h.ticker}</td>
                  <td>{formatNum(h.quantity, 4)}</td>
                  <td>{sym}{formatNum(h.avg_buy)}</td>
                  <td>
                    {h.current_price !== null && h.current_price !== undefined
                      ? `${sym}${formatNum(h.current_price)}`
                      : '—'}
                  </td>
                  <td className={getPLClass(plInr)}>
                    ₹{formatNum(plInr)}
                  </td>
                  <td className={getPLClass(h.pl_pct)}>
                    {formatNum(h.pl_pct)}%
                  </td>
                  <td>{h.currency}</td>
                  <td>{h.region || '—'}</td>
                  <td>{h.broker}</td>
                  <td>
                    {h.rec && (
                      <span style={{ ...REC_STYLES[h.rec], padding: '4px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 700 }}>
                        {h.rec}
                      </span>
                    )}
                  </td>
                  <td style={{ opacity: expandedId === h.id ? 1.0 : 0.4, userSelect: 'none' }}>›</td>
                </tr>
                {expandedId === h.id && (
                  <tr className="expanded-row">
                    <td colSpan={11}>
                      <div className="signals-panel">
                        <div className="signals-row">
                          <span>RSI: {h.rsi_14 ?? '—'}</span>
                          <span>MACD: {h.macd ?? '—'}</span>
                          <span>SMA50: {h.sma_50 ?? '—'}</span>
                          <span>SMA200: {h.sma_200 ?? '—'}</span>
                        </div>
                        <div className="signals-row">
                          <span>Analyst: {h.analyst_rating ?? 'No analyst coverage'}</span>
                          {h.analyst_target && <span>Target: {h.currency === 'EUR' ? '€' : '₹'}{h.analyst_target}</span>}
                          {h.analyst_num && <span>({h.analyst_num} analysts)</span>}
                        </div>
                        {h.ai_narrative
                          ? <p className="ai-narrative">{h.ai_narrative}</p>
                          : <p className="ai-narrative" style={{ color: 'var(--color-text-secondary)' }}>AI synthesis unavailable</p>
                        }
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="summary-row">
            <td colSpan={4}><strong>Total</strong></td>
            <td className={getPLClass(totalPlInr)}>
              <strong>₹{formatNum(totalPlInr)}</strong>
            </td>
            <td></td>
            <td colSpan={5}>
              <span style={{ color: 'var(--color-neutral)', fontSize: '12px' }}>
                (EUR equiv: €{formatNum(totalPlEur)})
                {' '}
                (${totalUsd ? formatNum(totalUsd) : '—'} USD)
              </span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
