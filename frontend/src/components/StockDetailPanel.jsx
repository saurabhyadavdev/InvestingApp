import { useState, useEffect } from 'react';
import { fetchStockDetail } from '../api.js';

const REC_STYLES = {
  BUY:  { background: '#28A745', color: '#fff' },
  SELL: { background: '#DC3545', color: '#fff' },
  HOLD: { background: '#6C757D', color: '#fff' },
};

/**
 * StockDetailPanel
 * Expanded row panel showing live-fetched signals, analyst data, and AI analysis for a holding.
 *
 * Props:
 *   ticker        {string} - yfinance ticker symbol
 *   currencySymbol {string} - "₹", "€", or "$"
 */
export default function StockDetailPanel({ ticker, currencySymbol }) {
  const [signalsData, setSignalsData] = useState(null);
  const [analystData, setAnalystData] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [signalsLoading, setSignalsLoading] = useState(true);
  const [analystLoading, setAnalystLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [activeTab, setActiveTab] = useState('signals');

  useEffect(() => {
    fetchStockDetail(ticker)
      .then(data => {
        setSignalsData(data.signals);
        setAnalystData(data.analyst);
        setAiData(data.ai);
        setSignalsLoading(false);
        setAnalystLoading(false);
        setAiLoading(false);
      })
      .catch(err => {
        setFetchError(err.message);
        setSignalsLoading(false);
        setAnalystLoading(false);
        setAiLoading(false);
      });
  }, [ticker]);

  const tabs = [
    { key: 'signals', label: 'Signals' },
    { key: 'analyst', label: 'Analyst' },
    { key: 'ai', label: 'AI Analysis' },
  ];

  const isActiveTabLoading = activeTab === 'signals'
    ? signalsLoading
    : activeTab === 'analyst'
      ? analystLoading
      : aiLoading;

  function renderTabContent() {
    if (fetchError) {
      return <p style={{ fontSize: 14, color: '#DC3545' }}>Failed to load detail.</p>;
    }

    if (activeTab === 'signals') {
      if (signalsLoading) {
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0' }}>
            <div className="typing-dots"><span>•</span><span>•</span><span>•</span></div>
          </div>
        );
      }
      if (!signalsData) {
        return (
          <p style={{ fontSize: 14, color: '#6C757D', padding: '16px 0' }}>
            Signal data unavailable for this holding.
          </p>
        );
      }
      const rsi = signalsData.rsi_14;
      const rsiQualifier = rsi != null && rsi < 30
        ? <span style={{ color: '#DC3545' }}> (oversold)</span>
        : rsi != null && rsi > 70
          ? <span style={{ color: '#28A745' }}> (overbought)</span>
          : null;

      return (
        <div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontWeight: 600 }}>RSI:</span>{' '}
            {rsi != null ? <>{rsi.toFixed(1)}{rsiQualifier}</> : '—'}
          </div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontWeight: 600 }}>MACD:</span>{' '}
            {signalsData.macd != null ? signalsData.macd.toFixed(2) : '—'}
            <span style={{ color: '#6C757D' }}> / Signal: </span>
            {signalsData.macd_signal != null ? signalsData.macd_signal.toFixed(2) : '—'}
            <span style={{ color: '#6C757D' }}> / Hist: </span>
            {signalsData.macd_histogram != null ? signalsData.macd_histogram.toFixed(2) : '—'}
          </div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontWeight: 600 }}>SMA50:</span>{' '}
            {signalsData.sma_50 != null
              ? <>{currencySymbol}{signalsData.sma_50.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</>
              : '—'}
            <span style={{ color: '#6C757D' }}> · </span>
            <span style={{ fontWeight: 600 }}>SMA200:</span>{' '}
            {signalsData.sma_200 != null
              ? <>{currencySymbol}{signalsData.sma_200.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</>
              : '—'}
          </div>
        </div>
      );
    }

    if (activeTab === 'analyst') {
      if (analystLoading) {
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0' }}>
            <div className="typing-dots"><span>•</span><span>•</span><span>•</span></div>
          </div>
        );
      }
      if (!analystData || analystData.rating == null || analystData.rating === 'No coverage') {
        return (
          <p style={{ fontSize: 14, color: '#6C757D', padding: '16px 0' }}>
            No analyst coverage.
          </p>
        );
      }
      const recStyle = REC_STYLES[analystData.rating] || { background: '#6C757D', color: '#fff' };
      return (
        <div>
          <div style={{ marginBottom: 8 }}>
            <span style={{
              ...recStyle,
              padding: '4px 8px',
              borderRadius: 3,
              fontSize: 11,
              fontWeight: 700,
            }}>
              {analystData.rating}
            </span>
            {analystData.num_analysts != null && (
              <span style={{ color: '#6C757D', marginLeft: 8 }}>
                ({analystData.num_analysts} analysts)
              </span>
            )}
          </div>
          {analystData.target_mean != null && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>Target:</span>{' '}
              {currencySymbol}{analystData.target_mean.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          )}
        </div>
      );
    }

    if (activeTab === 'ai') {
      if (aiLoading) {
        return (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0' }}>
            <div className="typing-dots"><span>•</span><span>•</span><span>•</span></div>
            <p style={{ fontSize: 14, color: '#6C757D', marginTop: 8 }}>Generating analysis...</p>
          </div>
        );
      }
      if (!aiData) {
        return (
          <p style={{ fontSize: 14, color: '#6C757D', padding: '24px 0', textAlign: 'center' }}>
            AI analysis unavailable.
          </p>
        );
      }
      const sections = [
        { heading: "Today's Move", body: aiData.today_move },
        { heading: 'Recommendation', body: aiData.recommendation },
        { heading: 'Short-term Outlook', body: aiData.outlook },
      ];
      return (
        <div>
          {sections.map((section, idx) => (
            <div key={section.heading} style={{ marginTop: idx === 0 ? 0 : 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#212529', marginBottom: 8, marginTop: 0 }}>
                {section.heading}
              </h3>
              <p style={{
                fontSize: 14,
                fontWeight: 400,
                color: section.body ? '#212529' : '#6C757D',
                lineHeight: 1.5,
                margin: 0,
              }}>
                {section.body ?? (
                  section.heading === "Today's Move"
                    ? 'Price movement data unavailable.'
                    : section.heading === 'Recommendation'
                      ? 'Recommendation analysis unavailable.'
                      : 'Outlook data unavailable.'
                )}
              </p>
            </div>
          ))}
        </div>
      );
    }

    return null;
  }

  return (
    <div style={{ background: '#F8F9FA', padding: '16px 24px', borderTop: '1px solid #E0E0E0' }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #E0E0E0', marginBottom: 16 }}>
        {tabs.map(tab => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              role="tab"
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: isActive ? '2px solid #0066CC' : '2px solid transparent',
                padding: '8px 16px 8px 0',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#212529' : '#6C757D',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div role="tabpanel" aria-busy={isActiveTabLoading}>
        {renderTabContent()}
      </div>
    </div>
  );
}
