import { useState } from 'react';

/**
 * NewsCard
 * 4-tab news interface showing: My Holdings | India Macro | Germany/EU Macro | US Macro
 * Reads from briefing.news — all tabs fall back to empty state when data is unavailable.
 */
export default function NewsCard({ briefing }) {
  const [activeTab, setActiveTab] = useState('holdings');
  const news = briefing?.news || { holdings: [], india: [], germany: [], us: [] };

  const tabs = ['holdings', 'india', 'germany', 'us'];
  const tabLabels = {
    holdings: 'My Holdings',
    india: 'India Macro',
    germany: 'Germany/EU Macro',
    us: 'US Macro',
  };
  const emptyMessages = {
    holdings: 'No recent news for your holdings.',
    india: 'No recent India macro news.',
    germany: 'No recent Germany/EU macro news.',
    us: 'No recent US macro news.',
  };

  const articles = news[activeTab] || [];

  return (
    <section style={{
      background: 'var(--color-bg-card)',
      borderRadius: 8,
      padding: '20px 24px',
      border: '1px solid var(--color-border)',
    }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid var(--color-border)',
        marginBottom: 16,
      }}>
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid var(--color-accent)' : '2px solid transparent',
              padding: '8px 16px 6px 0',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {tabLabels[tab]}
          </button>
        ))}
      </div>

      {/* Article list */}
      {articles.length === 0 ? (
        <p style={{
          color: 'var(--color-text-secondary)',
          fontSize: 14,
          padding: '24px 0',
          textAlign: 'center',
          margin: 0,
        }}>
          {emptyMessages[activeTab]}
        </p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {articles.map((article, idx) => (
            <li
              key={idx}
              style={{
                marginBottom: 12,
                paddingBottom: 12,
                borderBottom: idx < articles.length - 1 ? '1px solid var(--color-border)' : 'none',
              }}
            >
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: 'var(--color-text-primary)',
                  textDecoration: 'none',
                  fontSize: 14,
                }}
              >
                {article.title}
              </a>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 4 }}>
                {article.source} · {article.time_ago}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
