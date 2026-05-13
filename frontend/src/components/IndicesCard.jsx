/**
 * IndicesCard — display Nifty 50, Sensex, DAX, S&P 500 with colored % change.
 *
 * Props:
 *   indices: Array of IndexEntry objects from GET /api/indices
 *            [{symbol, name, close, change_pct, date, market_label}]
 */

function formatNumber(value) {
  if (value == null) return '—';
  return value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(pct) {
  if (pct == null) return '—';
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

function ChangeIndicator({ change_pct }) {
  if (change_pct == null) return null;
  const isPositive = change_pct >= 0;
  const arrow = isPositive ? '↑' : '↓';
  const color = isPositive ? 'var(--color-positive)' : 'var(--color-negative)';
  return (
    <span style={{ color, fontWeight: 600, whiteSpace: 'nowrap' }}>
      {arrow} {Math.abs(change_pct).toFixed(2)}%
    </span>
  );
}

export default function IndicesCard({ indices }) {
  const hasData = indices && indices.length > 0;

  return (
    <section
      style={{
        background: 'var(--color-bg-card)',
        borderRadius: 8,
        padding: '16px 20px',
        border: '1px solid var(--color-border)',
      }}
    >
      {/* Section heading per UI-SPEC */}
      <h2
        style={{
          fontSize: 20,
          fontWeight: 600,
          margin: '0 0 12px 0',
          color: 'var(--color-text-primary)',
        }}
      >
        Market Indices
      </h2>

      {!hasData ? (
        <p
          style={{
            color: 'var(--color-text-secondary)',
            fontSize: 14,
            margin: 0,
          }}
        >
          Market data unavailable
        </p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th
                style={{
                  textAlign: 'left',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--color-text-secondary)',
                  padding: '4px 8px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                Index
              </th>
              <th
                style={{
                  textAlign: 'right',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--color-text-secondary)',
                  padding: '4px 8px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                Close
              </th>
              <th
                style={{
                  textAlign: 'right',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--color-text-secondary)',
                  padding: '4px 8px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                Change
              </th>
              <th
                style={{
                  textAlign: 'right',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--color-text-secondary)',
                  padding: '4px 8px',
                  borderBottom: '1px solid var(--color-border)',
                }}
              >
                Date
              </th>
            </tr>
          </thead>
          <tbody>
            {indices.map((entry) => (
              <tr key={entry.symbol}>
                <td
                  style={{
                    padding: '8px',
                    fontSize: 14,
                    fontWeight: 600,
                    color: 'var(--color-text-primary)',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  {entry.name || entry.market_label}
                </td>
                <td
                  style={{
                    padding: '8px',
                    fontSize: 14,
                    fontWeight: 400,
                    fontFamily: 'monospace',
                    textAlign: 'right',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  {formatNumber(entry.close)}
                </td>
                <td
                  style={{
                    padding: '8px',
                    fontSize: 14,
                    textAlign: 'right',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  <ChangeIndicator change_pct={entry.change_pct} />
                </td>
                <td
                  style={{
                    padding: '8px',
                    fontSize: 12,
                    color: 'var(--color-text-secondary)',
                    textAlign: 'right',
                    borderBottom: '1px solid var(--color-border)',
                  }}
                >
                  {entry.date}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
