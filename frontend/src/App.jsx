import React, { useState, useEffect } from 'react';
import { fetchPortfolio } from './api.js';
import './index.css';

function getPLClass(pl) {
  if (pl > 0) return 'pl-positive';
  if (pl < 0) return 'pl-negative';
  return 'pl-zero';
}

function PortfolioTable({ holdings }) {
  if (holdings.length === 0) {
    return (
      <div className="empty-state">
        <h2>No portfolio data yet</h2>
        <p>Import your Zerodha or Trade Republic CSV to see holdings, P&L, and allocation breakdown.</p>
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Qty</th>
          <th>Avg Buy</th>
          <th>Current</th>
          <th>P&amp;L</th>
          <th>P&amp;L %</th>
          <th>Currency</th>
        </tr>
      </thead>
      <tbody>
        {holdings.map((h) => (
          <tr key={h.id || h.ticker}>
            <td>{h.ticker}</td>
            <td>{h.quantity}</td>
            <td>{h.avg_buy?.toFixed(2)}</td>
            <td>{h.current_price?.toFixed(2)}</td>
            <td className={getPLClass(h.pl)}>{h.pl?.toFixed(2)}</td>
            <td className={getPLClass(h.pl_pct)}>{h.pl_pct?.toFixed(2)}%</td>
            <td>{h.currency}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
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

  const today = new Date().toLocaleDateString('en-GB', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>Morning Briefing</h1>
          <div className="header-subtitle">{today}</div>
        </div>
      </div>

      <div className="portfolio-section">
        <div className="section-title">Your Portfolio</div>

        {loading && <div className="loading">Loading...</div>}

        {error && (
          <div className="error">
            Failed to load portfolio data: {error}
          </div>
        )}

        {!loading && !error && portfolio && (
          <PortfolioTable holdings={portfolio.holdings || []} />
        )}
      </div>
    </div>
  );
}
