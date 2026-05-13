import React, { useMemo } from 'react';

/**
 * AllocationCard
 * Shows portfolio allocation by region as percentages + absolute values.
 * Uses non-semantic blue shades (never green/red) per UI-SPEC.
 */

// Blue-shade palette for allocation bars (non-semantic)
const REGION_COLORS = {
  india: '#0066CC',
  germany: '#3388DD',
  us: '#66AAEE',
  etf: '#99CCFF',
  unknown: '#CCD9E6',
  cash: '#E0E8F0',
};

const REGION_LABELS = {
  india: 'India (NSE/BSE)',
  germany: 'Germany (XETRA)',
  us: 'US Markets',
  etf: 'ETF',
  unknown: 'Other',
  cash: 'Cash',
};

function formatCurrency(amount, currency) {
  const sym = currency === 'EUR' ? '€' : '₹';
  return `${sym}${Math.abs(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export default function AllocationCard({ holdings, cashByBroker, fxRate = 90 }) {
  const { byRegion, totalValue } = useMemo(() => {
    if (!holdings || holdings.length === 0) {
      return { byRegion: {}, totalValue: 0 };
    }

    const regionMap = {};
    let total = 0;

    for (const h of holdings) {
      if (h.asset_type === 'cash') continue; // cash shown separately

      // Use current_price * qty if available, else avg_buy * qty (cost basis)
      const price = h.current_price !== null && h.current_price !== undefined
        ? h.current_price
        : h.avg_buy;
      const value = price * h.quantity;
      const valueInr = h.currency === 'EUR' ? value * fxRate : value;

      const region = h.region || 'unknown';
      if (!regionMap[region]) {
        regionMap[region] = { valueInr: 0, currency: h.currency };
      }
      regionMap[region].valueInr += valueInr;
      total += valueInr;
    }

    return { byRegion: regionMap, totalValue: total };
  }, [holdings, fxRate]);

  const zerodha_cash = cashByBroker?.zerodha ?? 0;
  const tr_cash = cashByBroker?.trade_republic ?? 0;
  const hasCash = zerodha_cash > 0 || tr_cash > 0;
  const hasHoldings = totalValue > 0;

  if (!hasHoldings && !hasCash) {
    return (
      <div className="allocation-card">
        <div className="section-title">Allocation</div>
        <p className="empty-text">No holdings to display allocation.</p>
      </div>
    );
  }

  const sortedRegions = Object.entries(byRegion).sort((a, b) => b[1].valueInr - a[1].valueInr);

  return (
    <div className="allocation-card">
      <div className="section-title">Allocation</div>

      {hasHoldings && (
        <div className="allocation-section">
          <h3>By Region</h3>
          {sortedRegions.map(([region, data]) => {
            const pct = totalValue > 0 ? (data.valueInr / totalValue) * 100 : 0;
            const color = REGION_COLORS[region] || REGION_COLORS.unknown;
            return (
              <div key={region} className="allocation-row">
                <span className="allocation-label">
                  {REGION_LABELS[region] || region}
                </span>
                <div className="allocation-bar-track">
                  <div
                    className="allocation-bar"
                    style={{ width: `${pct.toFixed(1)}%`, backgroundColor: color }}
                  />
                </div>
                <span className="allocation-pct">{pct.toFixed(1)}%</span>
                <span className="allocation-value">
                  ₹{Math.round(data.valueInr).toLocaleString('en-IN')}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {hasCash && (
        <div className="allocation-section">
          <h3>Cash Balances</h3>
          {zerodha_cash > 0 && (
            <div className="allocation-row">
              <span className="allocation-label">Zerodha</span>
              <span className="allocation-value">₹{zerodha_cash.toLocaleString('en-IN')}</span>
            </div>
          )}
          {tr_cash > 0 && (
            <div className="allocation-row">
              <span className="allocation-label">Trade Republic</span>
              <span className="allocation-value">€{tr_cash.toLocaleString('en-DE')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
