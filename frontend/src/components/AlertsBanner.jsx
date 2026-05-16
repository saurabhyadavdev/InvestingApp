import React, { useState } from 'react';

/**
 * AlertsBanner — sticky amber banner listing all fired alerts.
 *
 * Renders nothing when alertsFired is empty or null.
 * Includes a dismiss button (×) to hide the banner for the session;
 * the underlying data in the briefing is unchanged.
 *
 * Props:
 *   alertsFired {Array<{ticker, type, message}>} - Alerts from briefing.alerts_fired
 *   onDismiss {function} - Optional callback when user clicks ×
 */
export default function AlertsBanner({ alertsFired, onDismiss }) {
  const [dismissed, setDismissed] = useState(false);

  if (!alertsFired || alertsFired.length === 0) return null;
  if (dismissed) return null;

  function handleDismiss() {
    setDismissed(true);
    if (onDismiss) onDismiss();
  }

  return (
    <div
      role="alert"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: '#FFF3CD',
        border: '1px solid #FFC107',
        borderRadius: 4,
        padding: '12px 16px',
        marginBottom: 16,
        fontSize: 13,
        color: '#856404',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
      }}
    >
      <div style={{ flex: 1 }}>
        <strong style={{ fontSize: 14 }}>&#9888; Active Alerts</strong>
        <ul style={{ margin: '6px 0 0 0', paddingLeft: 18, listStyle: 'disc' }}>
          {alertsFired.map((alert, i) => (
            <li key={i} style={{ marginBottom: 2 }}>
              {alert.message}
            </li>
          ))}
        </ul>
      </div>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss alerts"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: '#856404',
          fontSize: 18,
          lineHeight: 1,
          padding: '0 2px',
          opacity: 0.7,
          flexShrink: 0,
        }}
        onMouseEnter={e => { e.currentTarget.style.opacity = '1'; }}
        onMouseLeave={e => { e.currentTarget.style.opacity = '0.7'; }}
      >
        &times;
      </button>
    </div>
  );
}
