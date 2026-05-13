import React, { useState, useEffect, useCallback } from 'react';
import { fetchPortfolio } from './api.js';
import ImportCSV from './components/ImportCSV.jsx';
import PortfolioTable from './components/PortfolioTable.jsx';
import AllocationCard from './components/AllocationCard.jsx';
import './index.css';

export default function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPortfolio = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchPortfolio()
      .then((data) => {
        setPortfolio(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const today = new Date().toLocaleDateString('en-GB', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  const holdings = portfolio?.holdings || [];
  const cashByBroker = portfolio?.cash_by_broker || {};

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>Morning Briefing</h1>
          <div className="header-subtitle">{today}</div>
        </div>
      </div>

      {/* ImportCSV — always visible at top */}
      <div className="portfolio-section">
        <div className="section-title">Import Holdings</div>
        <ImportCSV onImportSuccess={loadPortfolio} />
      </div>

      {/* Portfolio Table */}
      <div className="portfolio-section">
        <div className="section-title">Your Portfolio</div>

        {loading && <div className="loading">Loading...</div>}

        {error && (
          <div className="error">
            Failed to load portfolio data: {error}
          </div>
        )}

        {!loading && !error && (
          <PortfolioTable
            holdings={holdings}
            totalInr={portfolio?.total_inr ?? 0}
            totalEur={portfolio?.total_eur ?? 0}
          />
        )}
      </div>

      {/* Allocation Card — shown when there are holdings */}
      {!loading && !error && (
        <div className="portfolio-section">
          <AllocationCard
            holdings={holdings}
            cashByBroker={cashByBroker}
          />
        </div>
      )}
    </div>
  );
}
