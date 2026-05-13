/**
 * App — root component that fetches the unified briefing and renders Dashboard.
 *
 * Simplified in Plan 04: all data comes from a single GET /api/briefing call.
 * Direct calls to fetchPortfolio/fetchIndices/fetchFX removed here;
 * Dashboard receives all sections from the briefing response.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { fetchBriefing } from './api.js';
import Dashboard from './Dashboard.jsx';
import './index.css';

export default function App() {
  const [briefing, setBriefing] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadBriefing = useCallback(() => {
    setLoading(true);
    fetchBriefing()
      .then((data) => {
        setBriefing(data);
        setLoading(false);
      })
      .catch(() => {
        setBriefing(null);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadBriefing();
  }, [loadBriefing]);

  return (
    <Dashboard
      briefing={briefing}
      loading={loading}
      onRefresh={loadBriefing}
    />
  );
}
