/**
 * FXCard — display EUR/INR rate with 24h range, timestamp in IST, and alert threshold.
 *
 * Props:
 *   fx: FX response object from GET /api/fx
 *       {pair, rate, low, high, timestamp, alert_threshold}
 *   onSetAlert: function(threshold: number) => Promise — called when user sets alert
 */
import { useState } from 'react';

function toIST(utcTimestamp) {
  if (!utcTimestamp) return null;
  try {
    const d = new Date(utcTimestamp);
    return d.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return null;
  }
}

export default function FXCard({ fx, onSetAlert }) {
  const [alertInput, setAlertInput] = useState('');
  const [editing, setEditing] = useState(false);
  const [confirmMsg, setConfirmMsg] = useState('');
  const [alertError, setAlertError] = useState('');

  if (!fx) {
    return (
      <section
        style={{
          background: 'var(--color-bg-card)',
          borderRadius: 8,
          padding: '16px 20px',
          border: '1px solid var(--color-border)',
        }}
      >
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>EUR/INR</h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 14, marginTop: 8 }}>
          FX data unavailable
        </p>
      </section>
    );
  }

  const istTime = toIST(fx.timestamp);
  const hasAlert = fx.alert_threshold != null;
  const isAlertTriggered = fx?.alert_triggered === true;

  async function handleSetAlert(e) {
    e.preventDefault();
    setAlertError('');
    const threshold = parseFloat(alertInput);
    if (!alertInput || isNaN(threshold) || threshold <= 0) {
      setAlertError('Enter a valid positive number');
      return;
    }
    try {
      await onSetAlert(threshold);
      setConfirmMsg('Alert threshold set');
      setEditing(false);
      setAlertInput('');
      setTimeout(() => setConfirmMsg(''), 3000);
    } catch (err) {
      setAlertError(err.message || 'Failed to set alert');
    }
  }

  return (
    <section
      style={{
        background: 'var(--color-bg-card)',
        borderRadius: 8,
        padding: '16px 20px',
        border: isAlertTriggered ? '2px solid #FFC107' : '1px solid var(--color-border)',
      }}
    >
      {/* Alert banner — shown when rate has crossed threshold */}
      {isAlertTriggered && (
        <div style={{
          background: '#FFF3CD',
          border: '1px solid #FFC107',
          borderRadius: 4,
          padding: '8px 12px',
          marginBottom: 10,
          fontSize: 13,
          color: '#856404',
        }}>
          Rate has crossed alert threshold ({fx.alert_threshold != null ? fx.alert_threshold.toFixed(4) : ''})
        </div>
      )}

      {/* Heading */}
      <h2
        style={{
          fontSize: 20,
          fontWeight: 600,
          margin: '0 0 8px 0',
          color: 'var(--color-text-primary)',
        }}
      >
        EUR/INR
      </h2>

      {/* Rate (big monospace) */}
      <div
        style={{
          fontSize: 28,
          fontWeight: 600,
          fontFamily: 'monospace',
          color: 'var(--color-text-primary)',
          lineHeight: 1.2,
        }}
      >
        {fx.rate != null ? fx.rate.toFixed(4) : '—'}
      </div>

      {/* 24h range */}
      <div
        style={{
          fontSize: 12,
          color: 'var(--color-text-secondary)',
          marginTop: 6,
        }}
      >
        Low: {fx.low != null ? fx.low.toFixed(4) : '—'}&nbsp;&nbsp;|&nbsp;&nbsp;
        High: {fx.high != null ? fx.high.toFixed(4) : '—'}
      </div>

      {/* Timestamp — "as of {time} IST" */}
      {istTime && (
        <div
          style={{
            fontSize: 12,
            color: 'var(--color-text-secondary)',
            marginTop: 4,
          }}
        >
          as of {istTime} IST
        </div>
      )}

      {/* Alert threshold section */}
      <div style={{ marginTop: 12, borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
        {hasAlert && !editing ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, color: 'var(--color-text-primary)' }}>
              Alert threshold: <strong>{fx.alert_threshold.toFixed(4)}</strong>
            </span>
            <button
              onClick={() => {
                setEditing(true);
                setAlertInput(String(fx.alert_threshold));
                setConfirmMsg('');
              }}
              style={{
                fontSize: 12,
                color: 'var(--color-accent)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '2px 6px',
                textDecoration: 'underline',
              }}
            >
              Edit
            </button>
          </div>
        ) : editing || !hasAlert ? (
          <form onSubmit={handleSetAlert} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="number"
              step="0.0001"
              min="0"
              placeholder="e.g. 99.5"
              value={alertInput}
              onChange={(e) => setAlertInput(e.target.value)}
              style={{
                fontSize: 14,
                padding: '4px 8px',
                border: '1px solid var(--color-border)',
                borderRadius: 4,
                width: 100,
              }}
            />
            <button
              type="submit"
              style={{
                fontSize: 14,
                padding: '4px 12px',
                background: 'var(--color-accent)',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Set Alert
            </button>
            {editing && (
              <button
                type="button"
                onClick={() => { setEditing(false); setAlertError(''); }}
                style={{
                  fontSize: 12,
                  padding: '4px 8px',
                  background: 'none',
                  border: '1px solid var(--color-border)',
                  borderRadius: 4,
                  cursor: 'pointer',
                  color: 'var(--color-text-secondary)',
                }}
              >
                Cancel
              </button>
            )}
            {alertError && (
              <span style={{ fontSize: 12, color: 'var(--color-negative)' }}>{alertError}</span>
            )}
          </form>
        ) : null}

        {confirmMsg && (
          <p style={{ fontSize: 12, color: 'var(--color-positive)', margin: '6px 0 0 0' }}>
            {confirmMsg}
          </p>
        )}
      </div>
    </section>
  );
}
