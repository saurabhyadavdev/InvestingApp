"""
SQLite schema creation for InvestIQ Phase 1.

All timestamps stored as UTC ISO 8601 TEXT.
"""
import sqlite3
import os


def create_schema(db_path: str) -> None:
    """
    Create all Phase 1 tables in the SQLite database at db_path.
    Uses CREATE TABLE IF NOT EXISTS — safe to call on every startup.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Holdings: imported from CSV, canonical by ISIN
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            broker TEXT NOT NULL,
            ticker_local TEXT NOT NULL,
            isin TEXT UNIQUE,
            ticker_yfinance TEXT,
            name TEXT,
            units REAL NOT NULL,
            cost_per_unit REAL NOT NULL,
            currency TEXT NOT NULL,
            region TEXT,
            asset_type TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Price history: OHLCV cache per ticker+date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        )
    """)

    # Technical indicators: RSI/MACD/BB per ticker+date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            rsi_14 REAL,
            macd REAL,
            macd_signal REAL,
            macd_histogram REAL,
            bb_upper REAL,
            bb_mid REAL,
            bb_lower REAL,
            sma_50 REAL,
            sma_200 REAL,
            ema_20 REAL,
            computed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        )
    """)

    # FX rates: EUR/INR snapshots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fx_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair TEXT NOT NULL,
            rate REAL NOT NULL,
            low REAL,
            high REAL,
            timestamp TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pair, timestamp)
        )
    """)

    # Briefing snapshots: full briefing JSON archive
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS briefing_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            briefing_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Settings: key-value user preferences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Chat history: reserved for Phase 2
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # News cache: stores fetched news articles per query+date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            date TEXT NOT NULL,
            articles_json TEXT NOT NULL,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(query, date)
        )
    """)

    # Analyst cache: stores analyst ratings and price targets per symbol+date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyst_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            rating TEXT,
            target_mean REAL,
            num_analysts INTEGER,
            cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
    """)

    conn.commit()
    conn.close()
