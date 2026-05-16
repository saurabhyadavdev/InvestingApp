import React, { useEffect, useState } from 'react';
import { saveAlertSettings } from '../api';

/**
 * SettingsModal — Alert configuration modal.
 *
 * Four sections:
 *   1. Price Target Alerts (per holding)
 *   2. Daily Move Alerts (global threshold + enable toggle)
 *   3. RSI Alerts (global enable toggle)
 *   4. Analyst Rating Alerts (global enable toggle)
 *
 * Props:
 *   isOpen {boolean} - Whether the modal is visible
 *   onClose {function} - Called when the modal should close (Escape, Cancel, backdrop click)
 *   holdings {Array} - Holdings array from briefing.portfolio.holdings
 *   initialSettings {object|null} - Current settings from GET /api/alerts (or null)
 */
export default function SettingsModal({ isOpen, onClose, holdings, initialSettings }) {
  // ---- Form state ----
  const [priceTargets, setPriceTargets] = useState({});
  const [priceEnabled, setPriceEnabled] = useState({});
  const [dailyMovePct, setDailyMovePct] = useState(5);
  const [dailyMoveEnabled, setDailyMoveEnabled] = useState(false);
  const [rsiEnabled, setRsiEnabled] = useState(false);
  const [analystEnabled, setAnalystEnabled] = useState(false);

  // ---- Toast state ----
  const [saveSuccess, setSaveSuccess] = useState('');
  const [saveError, setSaveError] = useState('');

  // ---- Validation errors ----
  const [priceErrors, setPriceErrors] = useState({});
  const [dailyMoveError, setDailyMoveError] = useState('');

  // Populate form from initialSettings when modal opens
  useEffect(() => {
    if (!isOpen) return;
    if (!initialSettings) return;

    setPriceTargets(initialSettings.price_targets || {});
    setPriceEnabled(initialSettings.price_enabled || {});
    setDailyMovePct(
      initialSettings.daily_move_pct !== undefined
        ? initialSettings.daily_move_pct
        : 5
    );
    setDailyMoveEnabled(initialSettings.daily_move_enabled || false);
    setRsiEnabled(initialSettings.rsi_enabled || false);
    setAnalystEnabled(initialSettings.analyst_enabled || false);
  }, [isOpen, initialSettings]);

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return;
    function handler(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Holdings filtered to exclude cash entries
  const holdingsList = (holdings || []).filter(
    h => h.ticker_yfinance && h.ticker_yfinance !== 'CASH'
  );

  // ---- Validation ----
  function validateForm() {
    let valid = true;
    const errors = {};

    for (const h of holdingsList) {
      const ticker = h.ticker_yfinance;
      const val = priceTargets[ticker];
      if (val !== undefined && val !== '' && val !== null) {
        const num = Number(val);
        if (isNaN(num) || num <= 0) {
          errors[ticker] = 'Enter a valid price';
          valid = false;
        }
      }
    }
    setPriceErrors(errors);

    const pct = Number(dailyMovePct);
    if (isNaN(pct) || pct < 0 || pct > 100) {
      setDailyMoveError('Enter a percentage between 0–100');
      valid = false;
    } else {
      setDailyMoveError('');
    }

    return valid;
  }

  // ---- Save handler ----
  async function handleSave() {
    setSaveSuccess('');
    setSaveError('');

    if (!validateForm()) return;

    // Build price_targets payload — only include tickers with a value set
    const filteredTargets = {};
    const filteredEnabled = {};
    for (const h of holdingsList) {
      const ticker = h.ticker_yfinance;
      const val = priceTargets[ticker];
      if (val !== undefined && val !== '' && val !== null) {
        filteredTargets[ticker] = Number(val);
        filteredEnabled[ticker] = priceEnabled[ticker] !== false; // default true if set
      }
      // Always include enabled flag if it was explicitly set
      if (priceEnabled[ticker] !== undefined) {
        filteredEnabled[ticker] = priceEnabled[ticker];
      }
    }

    const payload = {
      price_targets: filteredTargets,
      price_enabled: filteredEnabled,
      daily_move_pct: Number(dailyMovePct),
      daily_move_enabled: dailyMoveEnabled,
      rsi_enabled: rsiEnabled,
      analyst_enabled: analystEnabled,
    };

    try {
      await saveAlertSettings(payload);
      setSaveSuccess('Alert settings saved successfully.');
      setTimeout(() => {
        setSaveSuccess('');
        onClose();
      }, 3000);
    } catch (err) {
      setSaveError(err.message || 'Failed to save alert settings. Please try again.');
      setTimeout(() => setSaveError(''), 3000);
    }
  }

  // ---- Styles ----
  const sectionHeadingStyle = {
    fontSize: 14,
    fontWeight: 600,
    textTransform: 'uppercase',
    color: '#6C757D',
    margin: '20px 0 8px 0',
    borderBottom: '1px solid #E0E0E0',
    paddingBottom: 4,
  };

  const descStyle = {
    fontSize: 14,
    color: '#6C757D',
    marginBottom: 12,
  };

  const inputStyle = (hasError) => ({
    border: hasError ? '1px solid #DC3545' : '1px solid #E0E0E0',
    borderRadius: 4,
    padding: '6px 8px',
    fontSize: 14,
    width: 80,
  });

  const errorTextStyle = {
    color: '#DC3545',
    fontSize: 12,
    marginTop: 2,
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="alert-modal-title"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: 8,
          padding: 24,
          maxWidth: 500,
          width: '90%',
          maxHeight: '90vh',
          overflowY: 'auto',
          border: '1px solid #E0E0E0',
          boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h2
            id="alert-modal-title"
            style={{ margin: 0, fontSize: 20, fontWeight: 600, color: '#212529' }}
          >
            Alert Configuration
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 20,
              color: '#6C757D',
              padding: '0 4px',
              lineHeight: 1,
            }}
          >
            &times;
          </button>
        </div>

        {/* ---- Section 1: Price Target Alerts ---- */}
        <div style={sectionHeadingStyle}>Price Target Alerts</div>
        <p style={descStyle}>
          Set a price target per holding. Alert fires when price crosses the target.
        </p>

        {holdingsList.length === 0 && (
          <p style={{ color: '#6C757D', fontSize: 14 }}>No holdings loaded yet.</p>
        )}

        {holdingsList.map((h) => {
          const ticker = h.ticker_yfinance;
          const hasError = !!priceErrors[ticker];
          return (
            <div key={ticker} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 100, fontSize: 13, fontWeight: 600, color: '#212529', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {h.ticker || ticker}
                </span>
                <input
                  type="number"
                  placeholder="Target price"
                  value={priceTargets[ticker] ?? ''}
                  onChange={(e) => {
                    setPriceTargets(prev => ({ ...prev, [ticker]: e.target.value }));
                    if (priceErrors[ticker]) {
                      setPriceErrors(prev => { const next = { ...prev }; delete next[ticker]; return next; });
                    }
                  }}
                  style={inputStyle(hasError)}
                  min="0"
                  step="any"
                />
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13, color: '#212529' }}>
                  <input
                    type="checkbox"
                    checked={priceEnabled[ticker] !== false}
                    onChange={(e) => setPriceEnabled(prev => ({ ...prev, [ticker]: e.target.checked }))}
                  />
                  Enabled
                </label>
              </div>
              {hasError && <div style={errorTextStyle}>{priceErrors[ticker]}</div>}
            </div>
          );
        })}

        {/* ---- Section 2: Daily Move Alerts ---- */}
        <div style={sectionHeadingStyle}>Daily Move Alerts</div>
        <p style={descStyle}>
          Alert fires when any holding moves more than this % in a day, up or down.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 14, color: '#212529' }}>Threshold:</label>
          <input
            type="number"
            value={dailyMovePct}
            onChange={(e) => {
              setDailyMovePct(e.target.value);
              setDailyMoveError('');
            }}
            style={{ ...inputStyle(!!dailyMoveError), width: 60 }}
            min="0"
            max="100"
            step="any"
            placeholder="5"
          />
          <span style={{ fontSize: 14, color: '#212529' }}>%</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 14, color: '#212529' }}>
            <input
              type="checkbox"
              checked={dailyMoveEnabled}
              onChange={(e) => setDailyMoveEnabled(e.target.checked)}
            />
            Enable
          </label>
        </div>
        {dailyMoveError && <div style={errorTextStyle}>{dailyMoveError}</div>}

        {/* ---- Section 3: RSI Alerts ---- */}
        <div style={sectionHeadingStyle}>RSI Alerts</div>
        <p style={descStyle}>
          Alert fires when RSI crosses 70 (overbought) or 30 (oversold). Applies to all holdings.
        </p>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: '#212529' }}>
          <input
            type="checkbox"
            checked={rsiEnabled}
            onChange={(e) => setRsiEnabled(e.target.checked)}
          />
          Enable RSI alerts
        </label>

        {/* ---- Section 4: Analyst Rating Alerts ---- */}
        <div style={sectionHeadingStyle}>Analyst Rating Alerts</div>
        <p style={descStyle}>
          Alert fires when consensus rating changes (e.g., HOLD &rarr; BUY).
        </p>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, color: '#212529' }}>
          <input
            type="checkbox"
            checked={analystEnabled}
            onChange={(e) => setAnalystEnabled(e.target.checked)}
          />
          Enable analyst alerts
        </label>

        {/* ---- Toast messages ---- */}
        {saveSuccess && (
          <div style={{
            marginTop: 12,
            padding: '8px 12px',
            background: '#D4EDDA',
            border: '1px solid #28A745',
            borderRadius: 4,
            color: '#155724',
            fontSize: 13,
          }}>
            {saveSuccess}
          </div>
        )}
        {saveError && (
          <div style={{
            marginTop: 12,
            padding: '8px 12px',
            background: '#F8D7DA',
            border: '1px solid #DC3545',
            borderRadius: 4,
            color: '#721C24',
            fontSize: 13,
          }}>
            {saveError}
          </div>
        )}

        {/* ---- Footer buttons ---- */}
        <div style={{
          marginTop: 24,
          borderTop: '1px solid #E0E0E0',
          paddingTop: 16,
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 12,
        }}>
          <button
            onClick={onClose}
            style={{
              fontSize: 14,
              fontWeight: 600,
              padding: '8px 16px',
              background: 'transparent',
              border: '1px solid #E0E0E0',
              borderRadius: 4,
              cursor: 'pointer',
              color: '#212529',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#F8F9FA'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              fontSize: 14,
              fontWeight: 600,
              padding: '8px 16px',
              background: '#0066CC',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              color: '#FFFFFF',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#0052A3'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#0066CC'; }}
          >
            Save Alert Settings
          </button>
        </div>
      </div>
    </div>
  );
}
