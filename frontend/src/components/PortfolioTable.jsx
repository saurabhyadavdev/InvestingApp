import React, { useState } from 'react';

/**
 * PortfolioTable
 * Dense table showing holdings for a single broker with P&L.
 * broker="zerodha"         → primary P&L in INR
 * broker="trade_republic"  → primary P&L in EUR
 */

function getCurrencySymbol(currency) {
  if (currency === 'EUR') return '€';
  if (currency === 'INR') return '₹';
  if (currency === 'USD') return '$';
  return currency;
}

function getPLClass(value) {
  if (value > 0) return 'pl-positive';
  if (value < 0) return 'pl-negative';
  return 'pl-zero';
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

const REGION_LABELS = {
  germany: '🇩🇪',
  us: '🇺🇸',
  etf: 'ETF',
  nordic: '🇸🇪',
  india: '🇮🇳',
  unknown: '—',
};

export default function PortfolioTable({
  holdings,
  totalInr,
  totalEur,
  totalUsd = 0,
  fxRate = 90,
  alertTickers,
  broker = 'zerodha',
}) {
  const _alertSet = alertTickers instanceof Set
    ? alertTickers
    : new Set(alertTickers || []);
  const [expandedId, setExpandedId] = useState(null);

  const isZerodha = broker === 'zerodha';
  const plCurrency = isZerodha ? 'INR' : 'EUR';
  const plSymbol = isZerodha ? '₹' : '€';
  const isTradersPlace = broker === 'traders_place';

  if (!holdings || holdings.length === 0) {
    return (
      <div style={{ color: 'var(--color-text-secondary)', fontSize: '13px', padding: '12px 0' }}>
        No holdings imported yet.
      </div>
    );
  }

  const totalPl = holdings.reduce((sum, h) => {
    if (isZerodha) {
      return sum + (h.currency === 'EUR' ? (h.pl || 0) * fxRate : (h.pl || 0));
    } else {
      return sum + (h.currency === 'INR' ? (h.pl || 0) / fxRate : (h.pl || 0));
    }
  }, 0);

  const totalDayPl = holdings.reduce((sum, h) => {
    if (h.day_change == null) return sum;
    if (isZerodha) {
      return sum + (h.currency === 'EUR' ? h.day_change * fxRate : h.day_change);
    } else {
      return sum + (h.currency === 'INR' ? h.day_change / fxRate : h.day_change);
    }
  }, 0);
  const hasDayData = holdings.some(h => h.day_change != null);

  return (
    <div className="portfolio-table-wrapper">
      <table className="portfolio-table">
        <thead>
          <tr>
            <th>Ticker</th>
            {!isZerodha && <th>Name</th>}
            <th>Qty</th>
            <th>{isTradersPlace ? 'Stmt Price' : 'Avg Buy'}</th>
            <th>Current</th>
            <th>Today</th>
            <th>P&amp;L ({plCurrency})</th>
            <th>P&amp;L %</th>
            {!isZerodha && <th>Region</th>}
            <th>Rec</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, idx) => {
            const sym = getCurrencySymbol(h.currency);
            const plPrimary = isZerodha
              ? (h.currency === 'EUR' ? (h.pl || 0) * fxRate : (h.pl || 0))
              : (h.currency === 'INR' ? (h.pl || 0) / fxRate : (h.pl || 0));
            const dayPlPrimary = h.day_change == null ? null : (
              isZerodha
                ? (h.currency === 'EUR' ? h.day_change * fxRate : h.day_change)
                : (h.currency === 'INR' ? h.day_change / fxRate : h.day_change)
            );
            const rowKey = h.id || `${h.broker}-${h.ticker}-${idx}`;
            const hasAlert = _alertSet.has(h.ticker_yfinance) || _alertSet.has(h.ticker);
            return (
              <React.Fragment key={rowKey}>
                <tr
                  onClick={() => setExpandedId(expandedId === h.id ? null : h.id)}
                  style={{
                    cursor: 'pointer',
                    background: hasAlert ? 'rgba(255, 193, 7, 0.12)' : undefined,
                  }}
                >
                  <td>
                    <span style={{ fontWeight: 600 }}>{h.ticker}</span>
                    {h.asset_type === 'etf' && (
                      <span style={{ marginLeft: 4, fontSize: '10px', background: '#E3F2FD', color: '#0066CC', padding: '1px 4px', borderRadius: 3 }}>ETF</span>
                    )}
                  </td>
                  {!isZerodha && (
                    <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {h.name || '—'}
                    </td>
                  )}
                  <td>{formatNum(h.quantity, 4)}</td>
                  <td>{sym}{formatNum(h.avg_buy)}</td>
                  <td>
                    {h.current_price != null
                      ? `${sym}${formatNum(h.current_price)}`
                      : '—'}
                  </td>
                  <td className={getPLClass(dayPlPrimary)}>
                    {dayPlPrimary != null
                      ? `${plSymbol}${formatNum(dayPlPrimary)} (${formatNum(h.day_change_pct)}%)`
                      : '—'}
                  </td>
                  <td className={getPLClass(plPrimary)}>
                    {plSymbol}{formatNum(plPrimary)}
                  </td>
                  <td className={getPLClass(h.pl_pct)}>
                    {formatNum(h.pl_pct)}%
                  </td>
                  {!isZerodha && (
                    <td style={{ fontSize: '13px' }}>
                      {REGION_LABELS[h.region] || h.region || '—'}
                    </td>
                  )}
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
                    <td colSpan={isZerodha ? 10 : 11}>
                      <div className="signals-panel">
                        <div className="signals-row">
                          <span>RSI: {h.rsi_14 ?? '—'}</span>
                          <span>MACD: {h.macd ?? '—'}</span>
                          <span>SMA50: {h.sma_50 ?? '—'}</span>
                          <span>SMA200: {h.sma_200 ?? '—'}</span>
                        </div>
                        <div className="signals-row">
                          <span>Analyst: {h.analyst_rating ?? 'No analyst coverage'}</span>
                          {h.analyst_target && <span>Target: {sym}{h.analyst_target}</span>}
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
            <td colSpan={isZerodha ? 4 : 5}><strong>Total P&amp;L</strong></td>
            <td className={getPLClass(hasDayData ? totalDayPl : null)}>
              <strong>
                {hasDayData ? `${plSymbol}${formatNum(totalDayPl)}` : '—'}
              </strong>
            </td>
            <td className={getPLClass(totalPl)}>
              <strong>{plSymbol}{formatNum(totalPl)}</strong>
            </td>
            <td colSpan={isZerodha ? 3 : 4}>
              {isZerodha ? (
                <span style={{ color: 'var(--color-neutral)', fontSize: '12px' }}>
                  (€{formatNum(totalPl / fxRate)} EUR equiv)
                </span>
              ) : (
                <span style={{ color: 'var(--color-neutral)', fontSize: '12px' }}>
                  (₹{formatNum(totalPl * fxRate)} INR equiv)
                </span>
              )}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
