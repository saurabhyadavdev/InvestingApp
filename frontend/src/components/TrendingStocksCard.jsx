import React, { useEffect, useState } from 'react';

function fmt(n, decimals = 2) {
  return typeof n === 'number' ? n.toFixed(decimals) : '—';
}

function fmtVol(v) {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + 'K';
  return String(v);
}

function MarketColumn({ label, stocks, loading }) {
  return (
    <div style={styles.col}>
      <div style={styles.colHeader}>{label}</div>
      {loading ? (
        <div style={styles.empty}>Loading…</div>
      ) : stocks.length === 0 ? (
        <div style={styles.empty}>No data</div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Ticker</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>Price</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>Chg%</th>
              <th style={{ ...styles.th, textAlign: 'right' }}>Volume</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((s) => {
              const pos = s.change_pct >= 0;
              return (
                <tr key={s.ticker} style={styles.row}>
                  <td style={styles.ticker}>{s.ticker.replace(/\.(NS|DE)$/, '')}</td>
                  <td style={styles.num}>{fmt(s.close)}</td>
                  <td style={{ ...styles.num, color: pos ? '#2A9D8F' : '#E63946', fontWeight: 600 }}>
                    {pos ? '+' : ''}{fmt(s.change_pct)}%
                  </td>
                  <td style={{ ...styles.num, color: '#90A4AE' }}>{fmtVol(s.volume)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function TrendingStocksCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/trending')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const marketKeys = ['india', 'germany', 'us'];

  return (
    <div style={styles.wrapper}>
      <div style={styles.sectionTitle}>
        Trending — Most Traded Today
        {data?.fetched_at && (
          <span style={styles.fetchTime}>
            {' '}· {new Date(data.fetched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
      {error ? (
        <div style={styles.errorMsg}>Could not load trending data: {error}</div>
      ) : (
        <div style={styles.grid}>
          {marketKeys.map(key => {
            const market = data?.markets?.[key];
            return (
              <MarketColumn
                key={key}
                label={market?.label ?? key}
                stocks={market?.stocks ?? []}
                loading={loading}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    margin: '0 32px 0',
    padding: '16px',
    background: '#fff',
    borderRadius: 8,
    border: '1px solid #E9ECEF',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 700,
    color: '#212529',
    marginBottom: 12,
  },
  fetchTime: {
    fontWeight: 400,
    color: '#90A4AE',
    fontSize: 12,
  },
  grid: {
    display: 'flex',
    gap: 16,
    flexWrap: 'wrap',
  },
  col: {
    flex: 1,
    minWidth: 220,
  },
  colHeader: {
    fontSize: 12,
    fontWeight: 700,
    color: '#0066CC',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 6,
    borderBottom: '1px solid #E9ECEF',
    paddingBottom: 4,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 12,
  },
  th: {
    fontWeight: 600,
    color: '#6C757D',
    padding: '3px 4px',
    textAlign: 'left',
    borderBottom: '1px solid #F1F3F5',
  },
  row: {
    borderBottom: '1px solid #F8F9FA',
  },
  ticker: {
    padding: '4px 4px',
    fontWeight: 600,
    color: '#212529',
    fontFamily: 'monospace',
    fontSize: 12,
  },
  num: {
    padding: '4px 4px',
    textAlign: 'right',
    color: '#495057',
  },
  empty: {
    fontSize: 12,
    color: '#90A4AE',
    padding: '8px 0',
  },
  errorMsg: {
    fontSize: 12,
    color: '#E63946',
  },
};
