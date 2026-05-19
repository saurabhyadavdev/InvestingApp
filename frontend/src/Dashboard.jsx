/**
 * Dashboard — the unified morning briefing display component.
 *
 * Renders the complete briefing page from a single `briefing` prop
 * (the response from GET /api/briefing).
 *
 * Layout (per UI-SPEC Page Structure):
 *   1. Header: "Morning Briefing" + optional "Refresh Now" button
 *   2. ImportCSV
 *   3. Your Portfolio (PortfolioTable)
 *   4. Allocation (AllocationCard)
 *   5. Market Indices (IndicesCard)
 *   6. EUR/INR Rate (FXCard)
 *   7. Footer: "Last updated: {time} IST, {date}"
 */
import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { triggerRefresh, setFXAlert, fetchAlertSettings } from './api.js';
import ImportCSV from './components/ImportCSV.jsx';
import AlertsBanner from './components/AlertsBanner.jsx';
import SettingsModal from './components/SettingsModal.jsx';
import PortfolioTable from './components/PortfolioTable.jsx';
import AllocationCard from './components/AllocationCard.jsx';
import HeatMapCard from './components/HeatMapCard.jsx';
import IndicesCard from './components/IndicesCard.jsx';
import BenchmarkCard from './components/BenchmarkCard.jsx';
import FXCard from './components/FXCard.jsx';
import NewsCard from './components/NewsCard.jsx';
import ChatPanel from './components/ChatPanel.jsx';
import WeatherWidget from './components/WeatherWidget.jsx';

/**
 * Format a UTC ISO timestamp to "HH:MM IST, YYYY-MM-DD" for the footer.
 * @param {string} isoTimestamp - ISO 8601 UTC timestamp string
 * @returns {string} Formatted timestamp in IST
 */
function formatIST(isoTimestamp) {
  if (!isoTimestamp) return 'Unknown';
  try {
    const date = new Date(isoTimestamp);
    const timeIST = date.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    });
    const dateIST = date.toLocaleDateString('en-CA', {
      timeZone: 'Asia/Kolkata',
    }); // YYYY-MM-DD
    return `${timeIST} IST, ${dateIST}`;
  } catch {
    return isoTimestamp;
  }
}

/**
 * Determine if "Refresh Now" button should be visible.
 * Show if: current local hour >= 12 OR briefing is older than 6 hours.
 * @param {string|undefined} generatedAt - ISO 8601 generated_at timestamp
 * @returns {boolean}
 */
function shouldShowRefresh(generatedAt) {
  const now = new Date();
  const istHour = parseInt(
    now.toLocaleTimeString('en-US', { hour: 'numeric', hour12: false, timeZone: 'Asia/Kolkata' }),
    10
  );
  if (istHour >= 12) return true;
  if (!generatedAt) return false;
  const generated = new Date(generatedAt);
  const diffHours = (now - generated) / (1000 * 60 * 60);
  return diffHours > 6;
}

/**
 * Format briefing_date (YYYY-MM-DD) to a human-readable full date string.
 * @param {string} dateStr - YYYY-MM-DD
 * @returns {string} e.g. "Wednesday, 13 May 2026"
 */
function formatBriefingDate(dateStr) {
  if (!dateStr) return '';
  try {
    // Parse as local date (no timezone shift for a date-only string)
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString('en-GB', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Dashboard component — renders the complete morning briefing.
 *
 * Props:
 *   briefing {object|null} - Full briefing response from GET /api/briefing (null = loading/error)
 *   loading {boolean} - True while initial fetch is in progress
 *   onRefresh {function} - Callback to reload briefing after refresh
 */
const TABS = [
  { id: 'overview',       label: 'Overview' },
  { id: 'zerodha',        label: '🇮🇳 Zerodha' },
  { id: 'trade_republic', label: '🇩🇪 Trade Republic' },
  { id: 'traders_place',  label: '🏦 Traders Place' },
];

export default function Dashboard({ briefing, loading, onRefresh }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);

  // Alert settings modal state
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [alertInitialSettings, setAlertInitialSettings] = useState(null);
  const [notifiedBriefingId, setNotifiedBriefingId] = useState(null);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
      if (onRefresh) await onRefresh();
    } catch (err) {
      console.error('Refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  const handleSetAlert = useCallback(async (threshold) => {
    await setFXAlert(threshold);
    if (onRefresh) await onRefresh();
  }, [onRefresh]);

  const handleImportSuccess = useCallback(async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
      if (onRefresh) await onRefresh();
    } catch (err) {
      console.error('Post-import refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  // Derive alerts from briefing (safe with null — returns empty array)
  const alertsFired = briefing?.alerts_fired ?? [];
  const alertTickers = useMemo(
    () => new Set(alertsFired.map(a => a.ticker)),
    [alertsFired]
  );

  // Browser notification — fires once per unique briefing when alerts exist and permission granted
  // NOTE: Notification.requestPermission() is NOT called here — it stays in handleOpenSettings
  useEffect(() => {
    if (alertsFired.length === 0) return;
    if (!briefing?.generated_at) return;
    if (briefing.generated_at === notifiedBriefingId) return;
    if (typeof Notification === 'undefined') return;
    if (Notification.permission !== 'granted') return;

    new Notification('InvestIQ Alert', {
      body: `${alertsFired.length} alert(s) triggered in your portfolio. Check the dashboard.`,
    });
    setNotifiedBriefingId(briefing.generated_at);
  }, [briefing?.generated_at, alertsFired.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Gear icon click handler — requestPermission MUST stay here (user gesture context, not useEffect)
  async function handleOpenSettings() {
    if ('Notification' in window && Notification.permission === 'default') {
      try { await Notification.requestPermission(); } catch (_) { /* ignore */ }
    }
    try {
      const s = await fetchAlertSettings();
      setAlertInitialSettings(s);
    } catch (_) {
      setAlertInitialSettings({});
    }
    setIsSettingsOpen(true);
  }

  // --- Loading state ---
  if (loading) {
    return (
      <div className="page">
        <WeatherWidget />
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '200px',
            fontSize: '14px',
            color: '#6C757D',
          }}
        >
          Loading briefing...
        </div>
      </div>
    );
  }

  // --- Error / null state ---
  if (!briefing) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Kolkata',
    });
    return (
      <div className="page">
        <WeatherWidget />
        <div className="header">
          <div>
            <h1>Morning Briefing</h1>
          </div>
        </div>
        <div className="portfolio-section">
          <div
            className="error"
            style={{ fontSize: '14px', padding: '16px' }}
          >
            Market data unavailable — {timeStr}. Last updated: unknown. Retry in 1 minute.
          </div>
        </div>
      </div>
    );
  }

  // --- Full briefing state ---
  const {
    portfolio = {},
    indices = {},
    fx = {},
    generated_at,
    briefing_date,
    fetched_at,
  } = briefing;

  const holdings = portfolio.holdings || [];
  const cashByBroker = portfolio.cash_by_broker || {};
  const totalInr = portfolio.total_inr || 0;
  const totalEur = portfolio.total_eur || 0;
  const totalUsd = portfolio.total_usd ?? 0;

  const zerodhaHoldings = holdings.filter(h => h.broker === 'zerodha');
  const trHoldings = holdings.filter(h => h.broker === 'trade_republic');
  const tpHoldings = holdings.filter(h => h.broker === 'traders_place');

  // Convert indices dict to array for IndicesCard (which expects array)
  const indicesArray = Object.values(indices || {});

  const showRefresh = shouldShowRefresh(generated_at);
  const dateLabel = formatBriefingDate(briefing_date);

  return (
    <div className="page" style={{ paddingBottom: '44px' }}>
      {/* Weather — always visible, independent fetch */}
      <WeatherWidget />

      {/* Header */}
      <div
        className="header"
        style={{
          padding: '24px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 600, lineHeight: 1.2 }}>
            Morning Briefing
          </h1>
          {dateLabel && (
            <div
              className="header-subtitle"
              style={{ fontSize: '14px', color: '#6C757D' }}
            >
              {dateLabel}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {showRefresh && (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              style={{
                backgroundColor: '#0066CC',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                padding: '8px 16px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: refreshing ? 'not-allowed' : 'pointer',
                opacity: refreshing ? 0.7 : 1,
              }}
            >
              {refreshing ? 'Refreshing…' : 'Refresh Now'}
            </button>
          )}
          <button
            onClick={handleOpenSettings}
            aria-label="Alert settings"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              color: '#0066CC',
              fontSize: 20,
              lineHeight: 1,
            }}
          >
            &#9881;
          </button>
        </div>
      </div>

      {/* Alert Banner */}
      <AlertsBanner alertsFired={alertsFired} />

      {/* Import Holdings — always visible */}
      <div className="portfolio-section">
        <ImportCSV onImportSuccess={handleImportSuccess} />
      </div>

      {/* Tab Bar */}
      <div
        style={{
          display: 'flex',
          gap: 0,
          borderBottom: '2px solid var(--color-border)',
          margin: '0 32px',
          marginBottom: 0,
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: isActive ? '2px solid #0066CC' : '2px solid transparent',
                marginBottom: '-2px',
                padding: '10px 20px',
                fontSize: '14px',
                fontWeight: isActive ? 700 : 400,
                color: isActive ? '#0066CC' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'color 0.15s',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab: Overview */}
      {activeTab === 'overview' && (
        <>
          <div className="portfolio-section">
            <HeatMapCard holdings={holdings} fxRate={fx?.rate ?? 90} />
          </div>
          <div className="portfolio-section">
            <AllocationCard
              holdings={holdings}
              cashByBroker={cashByBroker}
              fxRate={fx.rate ?? 90}
            />
          </div>
          <div className="portfolio-section">
            <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
              Market Indices
            </div>
            <IndicesCard indices={indicesArray} />
          </div>
          <div className="portfolio-section">
            <BenchmarkCard benchmarkData={briefing?.benchmark_data} />
          </div>
          <div className="portfolio-section">
            <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
              EUR/INR Rate
            </div>
            <FXCard
              fx={Object.keys(fx).length > 0 ? fx : null}
              onSetAlert={handleSetAlert}
            />
          </div>
          <div className="portfolio-section">
            <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
              Market Intelligence
            </div>
            <NewsCard briefing={briefing} />
          </div>
        </>
      )}

      {/* Tab: Zerodha */}
      {activeTab === 'zerodha' && (
        <>
          <div className="portfolio-section">
            {zerodhaHoldings.length === 0 ? (
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '13px', padding: '12px 0' }}>
                No Zerodha holdings. Import a Zerodha CSV above.
              </div>
            ) : (
              <PortfolioTable
                holdings={zerodhaHoldings}
                totalInr={totalInr}
                totalEur={totalEur}
                totalUsd={totalUsd}
                fxRate={fx.rate ?? 90}
                alertTickers={alertTickers}
                broker="zerodha"
              />
            )}
          </div>
          <div className="portfolio-section">
            <BenchmarkCard benchmarkData={briefing?.benchmark_data} />
          </div>
        </>
      )}

      {/* Tab: Trade Republic */}
      {activeTab === 'trade_republic' && (
        <>
          <div className="portfolio-section">
            {trHoldings.length === 0 ? (
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '13px', padding: '12px 0' }}>
                No Trade Republic holdings. Import a Trade Republic CSV above.
              </div>
            ) : (
              <PortfolioTable
                holdings={trHoldings}
                totalInr={totalInr}
                totalEur={totalEur}
                totalUsd={totalUsd}
                fxRate={fx.rate ?? 90}
                alertTickers={alertTickers}
                broker="trade_republic"
              />
            )}
          </div>
          <div className="portfolio-section">
            <BenchmarkCard benchmarkData={briefing?.benchmark_data} />
          </div>
        </>
      )}

      {/* Tab: Traders Place */}
      {activeTab === 'traders_place' && (
        <>
          <div className="portfolio-section">
            {tpHoldings.length === 0 ? (
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '13px', padding: '12px 0' }}>
                No Traders Place holdings. Import a quarterly PDF above.
                <span style={{ marginLeft: 8, fontSize: '11px', color: '#6C757D' }}>
                  (P&amp;L shown vs. last quarterly statement price)
                </span>
              </div>
            ) : (
              <>
                <div style={{ fontSize: '11px', color: '#6C757D', marginBottom: 8 }}>
                  P&amp;L shown vs. quarter-end price from last imported statement
                </div>
                <PortfolioTable
                  holdings={tpHoldings}
                  totalInr={totalInr}
                  totalEur={totalEur}
                  totalUsd={totalUsd}
                  fxRate={fx.rate ?? 90}
                  alertTickers={alertTickers}
                  broker="traders_place"
                />
              </>
            )}
          </div>
          <div className="portfolio-section">
            <BenchmarkCard benchmarkData={briefing?.benchmark_data} />
          </div>
        </>
      )}

      {/* Footer */}
      <footer
        style={{
          padding: '16px 32px',
          borderTop: '1px solid #E0E0E0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#6C757D',
          fontSize: '12px',
          marginTop: 24,
        }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-label="Last updated"
        >
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        Last updated: {formatIST(fetched_at || generated_at)}
      </footer>
      <ChatPanel briefing={briefing} />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        holdings={holdings}
        initialSettings={alertInitialSettings}
      />
    </div>
  );
}
