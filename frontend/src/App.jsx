/**
 * App — root component that fetches the unified briefing and renders Dashboard.
 *
 * Simplified in Plan 04: all data comes from a single GET /api/briefing call.
 * Direct calls to fetchPortfolio/fetchIndices/fetchFX removed here;
 * Dashboard receives all sections from the briefing response.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { fetchBriefing, refreshPrices } from './api.js';
import Dashboard from './Dashboard.jsx';
import './index.css';

export default function App() {
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);
  // True while the on-open background price refresh is in flight. Drives the
  // "Updating prices…" UI so the user never reads stale daily-% as current.
  const [pricesRefreshing, setPricesRefreshing] = useState(false);

  const loadBriefing = useCallback(() => {
    setLoading(true);
    return fetchBriefing()
      .then((data) => {
        setBriefing(data);
        setLoading(false);
      })
      .catch(() => {
        setBriefing(null);
        setLoading(false);
      });
  }, []);

  // Reload the snapshot WITHOUT flipping the full-page loading state — used for
  // the in-place update after a background price refresh lands.
  const reloadSilently = useCallback(() => {
    return fetchBriefing()
      .then((data) => setBriefing(data))
      .catch(() => {});
  }, []);

  // On open: show the cached snapshot immediately, then pull fresh market data
  // (indices, FX, holding prices) in the background and update in place once it
  // lands (~20s of yfinance I/O). Refresh failures are non-fatal — the cached
  // snapshot stays on screen.
  useEffect(() => {
    loadBriefing().finally(() => {
      setPricesRefreshing(true);
      refreshPrices()
        .then(reloadSilently)
        .catch(() => {})
        .finally(() => setPricesRefreshing(false));
    });
  }, [loadBriefing, reloadSilently]);

  return (
    <Dashboard
      briefing={briefing}
      loading={loading}
      onRefresh={loadBriefing}
      pricesRefreshing={pricesRefreshing}
    />
  );
}
