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
import React, { useState, useCallback } from 'react';
import { triggerRefresh, setFXAlert } from './api.js';
import ImportCSV from './components/ImportCSV.jsx';
import PortfolioTable from './components/PortfolioTable.jsx';
import AllocationCard from './components/AllocationCard.jsx';
import HeatMapCard from './components/HeatMapCard.jsx';
import IndicesCard from './components/IndicesCard.jsx';
import FXCard from './components/FXCard.jsx';
import NewsCard from './components/NewsCard.jsx';
import ChatPanel from './components/ChatPanel.jsx';

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
export default function Dashboard({ briefing, loading, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false);

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

  // --- Loading state ---
  if (loading) {
    return (
      <div className="page">
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

  // Convert indices dict to array for IndicesCard (which expects array)
  const indicesArray = Object.values(indices || {});

  const showRefresh = shouldShowRefresh(generated_at);
  const dateLabel = formatBriefingDate(briefing_date);

  return (
    <div className="page" style={{ paddingBottom: '44px' }}>
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
      </div>

      {/* Import Holdings */}
      <div className="portfolio-section">
        <ImportCSV onImportSuccess={handleImportSuccess} />
      </div>

      {/* Your Portfolio */}
      <div className="portfolio-section">
        <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
          Your Portfolio
        </div>
        <PortfolioTable
          holdings={holdings}
          totalInr={totalInr}
          totalEur={totalEur}
          totalUsd={totalUsd}
          fxRate={fx.rate ?? 90}
        />
      </div>

      {/* Allocation */}
      <div className="portfolio-section">
        <AllocationCard
          holdings={holdings}
          cashByBroker={cashByBroker}
          fxRate={fx.rate ?? 90}
        />
      </div>

      {/* Portfolio Heat Map */}
      <div className="portfolio-section">
        <HeatMapCard holdings={holdings} fxRate={fx?.rate ?? 90} />
      </div>

      {/* Market Indices */}
      <div className="portfolio-section">
        <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
          Market Indices
        </div>
        <IndicesCard indices={indicesArray} />
      </div>

      {/* EUR/INR Rate */}
      <div className="portfolio-section">
        <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
          EUR/INR Rate
        </div>
        <FXCard
          fx={Object.keys(fx).length > 0 ? fx : null}
          onSetAlert={handleSetAlert}
        />
      </div>

      {/* Market Intelligence */}
      <div className="portfolio-section">
        <div className="section-title" style={{ fontSize: '20px', fontWeight: 600 }}>
          Market Intelligence
        </div>
        <NewsCard briefing={briefing} />
      </div>

      {/* Footer — Data Status */}
      <footer
        style={{
          padding: '16px 32px',
          borderTop: '1px solid #E0E0E0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#6C757D',
          fontSize: '12px',
        }}
      >
        {/* Clock icon (inline SVG Feather clock) */}
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
    </div>
  );
}
