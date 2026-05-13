import React from 'react';

/**
 * PortfolioTable
 * Dense table showing all holdings with P&L per UI-SPEC.
 * P&L cells colored: positive=green, negative=red, zero=neutral gray.
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

export default function PortfolioTable({ holdings, totalInr, totalEur, fxRate = 90 }) {
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
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, idx) => {
            const sym = getCurrencySymbol(h.currency);
            const plInr = h.currency === 'EUR'
              ? (h.pl || 0) * fxRate
              : (h.pl || 0);
            return (
              <tr key={h.id || `${h.broker}-${h.ticker}-${idx}`}>
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
              </tr>
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
            <td colSpan={3}>
              <span style={{ color: 'var(--color-neutral)', fontSize: '12px' }}>
                (EUR equiv: €{formatNum(totalPlEur)})
              </span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
