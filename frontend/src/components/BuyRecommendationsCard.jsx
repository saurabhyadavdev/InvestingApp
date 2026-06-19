import React, { useEffect, useState } from 'react';
import { fetchRecommendations } from '../api.js';

const MARKET_ORDER = ['india', 'germany', 'us'];

function SignalTag({ label }) {
  const isOversold = label.startsWith('Oversold');
  const isMacd = label.includes('MACD');
  const isPositive = label.startsWith('+');

  let bg = '#1E2A1A';
  let color = 'var(--color-positive)';
  if (isOversold) { bg = '#2A1A1E'; color = '#FF8C94'; }
  else if (isMacd) { bg = '#1A2235'; color = '#7AB8FF'; }
  else if (isPositive) { bg = '#1A2A1C'; color = 'var(--color-positive)'; }

  return (
    <span style={{
      fontSize: 11,
      fontWeight: 600,
      padding: '2px 7px',
      borderRadius: 10,
      background: bg,
      color,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}

function ScoreDots({ score }) {
  const max = 8;
  const filled = Math.min(score, max);
  return (
    <div style={{ display: 'flex', gap: 3, alignItems: 'center' }}>
      {Array.from({ length: max }).map((_, i) => (
        <div key={i} style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: i < filled ? 'var(--color-positive)' : 'var(--color-border)',
        }} />
      ))}
    </div>
  );
}

function PickRow({ pick }) {
  const isUp = pick.change_pct >= 0;
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: 12,
      padding: '10px 0',
      borderBottom: '1px solid var(--color-border)',
    }}>
      <div style={{ flex: '0 0 72px' }}>
        <div style={{ fontWeight: 700, fontSize: 13, fontFamily: 'monospace', color: 'var(--color-text-primary)' }}>
          {pick.name}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
          {pick.close.toLocaleString()}
        </div>
      </div>

      <div style={{ flex: '0 0 60px', textAlign: 'right' }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: isUp ? 'var(--color-positive)' : 'var(--color-negative)',
        }}>
          {isUp ? '+' : ''}{pick.change_pct.toFixed(2)}%
        </div>
        {pick.rsi_14 != null && (
          <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 2 }}>
            RSI {pick.rsi_14}
          </div>
        )}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {pick.signals.map((s, i) => <SignalTag key={i} label={s} />)}
        </div>
        <ScoreDots score={pick.score} />
      </div>
    </div>
  );
}

function MarketSection({ label, picks }) {
  if (!picks || picks.length === 0) return null;
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 12,
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        color: 'var(--color-accent)',
        marginBottom: 4,
      }}>
        {label}
      </div>
      {picks.map((p) => <PickRow key={p.ticker} pick={p} />)}
    </div>
  );
}

export default function BuyRecommendationsCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRecommendations()
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const anyPicks = data && MARKET_ORDER.some(k => data.markets?.[k]?.picks?.length > 0);

  return (
    <div style={{
      background: 'var(--color-bg-card)',
      border: '1px solid var(--color-border)',
      borderRadius: 8,
      padding: '20px 24px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--color-text-primary)' }}>
          Buy Opportunities
        </h2>
        <span style={{
          fontSize: 11,
          background: '#0D2B17',
          color: 'var(--color-positive)',
          padding: '3px 10px',
          borderRadius: 10,
          fontWeight: 700,
        }}>
          Signal-Based
        </span>
      </div>

      {loading && (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 14, padding: '8px 0' }}>
          Scanning market universe…
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--color-negative)', fontSize: 13 }}>
          Failed to load: {error}
        </div>
      )}

      {!loading && !error && !anyPicks && (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>
          No strong BUY signals found across the universe right now.
        </div>
      )}

      {!loading && !error && anyPicks && (
        <>
          <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 16 }}>
            Stocks scoring on RSI, MACD momentum, trend, and price action. Not financial advice.
          </div>
          {MARKET_ORDER.map((key) => {
            const m = data.markets[key];
            return m ? <MarketSection key={key} label={m.label} picks={m.picks} /> : null;
          })}
          <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 4 }}>
            Updated {new Date(data.fetched_at).toLocaleTimeString()}
          </div>
        </>
      )}
    </div>
  );
}
