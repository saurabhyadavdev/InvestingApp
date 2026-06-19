import React, { useState, useEffect, useCallback, useRef } from 'react';
import { fetchStockDetail, searchStocks } from '../api.js';

const STORAGE_KEY = 'investiq_watchlist';

const REC_COLORS = {
  BUY:  'var(--color-positive)',
  SELL: 'var(--color-negative)',
  HOLD: 'var(--color-text-secondary)',
};

function WatchlistRow({ ticker, onRemove }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchStockDetail(ticker)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [ticker]);

  const signals = data?.signals ?? {};
  const price = signals.current_price;
  const dayPct = signals.day_change_pct;
  const rsi = signals.rsi_14;
  const rec = data?.rec;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '10px 0',
      borderBottom: '1px solid var(--color-border)',
    }}>
      <div style={{ flex: '0 0 100px', fontWeight: 600, fontSize: 13 }}>{ticker}</div>

      {loading && (
        <div style={{ flex: 1, fontSize: 12, color: 'var(--color-text-secondary)' }}>Loading…</div>
      )}
      {error && (
        <div style={{ flex: 1, fontSize: 12, color: '#DC3545' }}>Error: {error}</div>
      )}
      {!loading && !error && (
        <>
          <div style={{ flex: '0 0 90px', fontSize: 13 }}>
            {price != null ? price.toLocaleString('en-US', { maximumFractionDigits: 2 }) : '—'}
          </div>
          <div style={{
            flex: '0 0 70px',
            fontSize: 13,
            color: dayPct == null ? 'var(--color-text-secondary)' : dayPct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)',
          }}>
            {dayPct != null ? `${dayPct >= 0 ? '+' : ''}${dayPct.toFixed(2)}%` : '—'}
          </div>
          <div style={{ flex: '0 0 60px', fontSize: 12, color: 'var(--color-text-secondary)' }}>
            RSI {rsi != null ? rsi.toFixed(1) : '—'}
          </div>
          {rec && (
            <div style={{
              flex: '0 0 52px',
              background: REC_COLORS[rec] ?? 'var(--color-text-secondary)',
              color: '#fff',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 700,
              padding: '2px 8px',
              textAlign: 'center',
            }}>
              {rec}
            </div>
          )}
        </>
      )}

      <button
        onClick={() => onRemove(ticker)}
        title="Remove from watchlist"
        style={{
          marginLeft: 'auto',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--color-text-secondary)',
          fontSize: 16,
          lineHeight: 1,
          padding: '2px 6px',
        }}
      >
        ×
      </button>
    </div>
  );
}

function StockSearchInput({ onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);
  const wrapperRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounceRef.current);
    if (!val.trim()) { setResults([]); setOpen(false); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchStocks(val.trim());
        setResults(res);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 350);
  };

  const handleSelect = (symbol) => {
    onSelect(symbol);
    setQuery('');
    setResults([]);
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative', flex: 1 }}>
      <input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder="Search stock by name or ticker…"
        style={{
          width: '100%',
          fontSize: 13,
          padding: '6px 10px',
          border: '1px solid var(--color-border)',
          borderRadius: 4,
          boxSizing: 'border-box',
          background: 'var(--color-bg-card)',
          color: 'var(--color-text-primary)',
        }}
      />
      {searching && (
        <div style={{
          position: 'absolute',
          right: 10,
          top: '50%',
          transform: 'translateY(-50%)',
          fontSize: 11,
          color: 'var(--color-text-secondary)',
        }}>
          …
        </div>
      )}
      {open && results.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: 'var(--color-bg-card)',
          border: '1px solid var(--color-border)',
          borderRadius: 4,
          boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
          zIndex: 200,
          maxHeight: 240,
          overflowY: 'auto',
        }}>
          {results.map((r) => (
            <div
              key={r.symbol}
              onMouseDown={() => handleSelect(r.symbol)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                display: 'flex',
                gap: 12,
                alignItems: 'center',
                fontSize: 13,
                borderBottom: '1px solid var(--color-border)',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-border)'}
              onMouseLeave={e => e.currentTarget.style.background = ''}
            >
              <span style={{ fontWeight: 700, flex: '0 0 90px' }}>{r.symbol}</span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {r.name}
              </span>
              {r.exchange && (
                <span style={{ fontSize: 11, color: 'var(--color-text-secondary)', flex: '0 0 auto' }}>
                  {r.exchange}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WatchlistCard() {
  const [tickers, setTickers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tickers));
  }, [tickers]);

  const handleAdd = useCallback((symbol) => {
    if (!symbol || tickers.includes(symbol)) return;
    setTickers(prev => [...prev, symbol]);
  }, [tickers]);

  const handleRemove = useCallback((ticker) => {
    setTickers(prev => prev.filter(t => t !== ticker));
  }, []);

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, gap: 16 }}>
        <div className="section-title" style={{ fontSize: '20px', fontWeight: 600, margin: 0, whiteSpace: 'nowrap' }}>
          Watchlist
        </div>
        <StockSearchInput onSelect={handleAdd} />
      </div>

      {tickers.length === 0 ? (
        <div style={{ fontSize: 13, color: 'var(--color-text-secondary)', padding: '8px 0' }}>
          No stocks on watchlist. Search for a stock above to add it.
        </div>
      ) : (
        <div>
          <div style={{
            display: 'flex',
            gap: 12,
            padding: '6px 0',
            borderBottom: '2px solid var(--color-border)',
            fontSize: 11,
            fontWeight: 600,
            color: 'var(--color-text-secondary)',
          }}>
            <div style={{ flex: '0 0 100px' }}>TICKER</div>
            <div style={{ flex: '0 0 90px' }}>PRICE</div>
            <div style={{ flex: '0 0 70px' }}>DAY %</div>
            <div style={{ flex: '0 0 60px' }}>RSI</div>
            <div style={{ flex: '0 0 52px' }}>REC</div>
          </div>
          {tickers.map(t => (
            <WatchlistRow key={t} ticker={t} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  );
}
