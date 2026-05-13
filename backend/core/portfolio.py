"""
Portfolio CSV import and P&L calculation for InvestIQ.

Supports:
  - Zerodha (NSE/BSE Indian stocks)
  - Trade Republic (German/US stocks and ETFs in EUR)

All SQLite inserts use parameterized ? placeholders — no f-string SQL.
"""
import csv
import logging
import sqlite3
import tempfile
import os
from typing import Union, IO

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_numeric(value: str) -> float:
    """Strip currency symbols, commas, and whitespace from a string and parse as float."""
    cleaned = value.replace("₹", "").replace(",", "").replace(" ", "").strip()
    if cleaned == "" or cleaned == "-":
        return 0.0
    return float(cleaned)


def _map_zerodha_exchange(exchange: str, ticker: str) -> tuple[str, str]:
    """
    Map exchange string to (region, ticker_yfinance).
    NSE → 'india', ticker.NS
    BSE → 'india', ticker.BO
    Defaults to NSE suffix for unknown exchanges.
    """
    exchange_upper = exchange.strip().upper()
    if exchange_upper == "BSE":
        return "india", f"{ticker}.BO"
    # Default NSE
    return "india", f"{ticker}.NS"


def _classify_asset_type(ticker_local: str, name: str = "") -> str:
    """
    Classify asset_type based on ticker or name.
    Returns 'cash', 'etf', or 'equity'.
    """
    if ticker_local.upper() == "CASHCOMPONENT":
        return "cash"
    name_upper = (name or "").upper()
    if "ETF" in name_upper or "ETF" in ticker_local.upper():
        return "etf"
    return "equity"


def _classify_tr_region(isin: str) -> str:
    """
    Classify region based on ISIN country prefix.
    DE → 'germany', US → 'us', IE/LU → 'etf', otherwise 'unknown'.
    """
    if not isin:
        return "unknown"
    prefix = isin[:2].upper()
    if prefix == "DE":
        return "germany"
    if prefix == "US":
        return "us"
    if prefix in ("IE", "LU"):
        return "etf"
    return "unknown"


def _open_csv_source(source: Union[str, IO]) -> tuple[csv.DictReader, bool]:
    """
    Accept either a file path (str) or a file-like object (IO).
    Returns a (csv.DictReader, owned) tuple where owned=True means the caller
    opened the file and is responsible for closing it.
    """
    if isinstance(source, str):
        # It's a file path — open it
        f = open(source, newline="", encoding="utf-8-sig")
        return csv.DictReader(f), True  # (reader, owned)
    else:
        # File-like object (e.g. io.StringIO or UploadFile content)
        return csv.DictReader(source), False


# ---------------------------------------------------------------------------
# Public function 1: import_zerodha_csv
# ---------------------------------------------------------------------------

def import_zerodha_csv(source: Union[str, IO], db_path: str) -> int:
    """
    Parse a Zerodha CSV (file path or file-like) and insert holdings into SQLite.

    Required columns: Trading Symbol, Quantity, Average Price, ISIN
    Optional: Exchange (defaults to NSE), Name (or Security name)

    Returns: count of rows inserted.
    Raises: ValueError if required columns are missing.
    """
    required_cols = {"Trading Symbol", "Quantity", "Average Price"}

    if isinstance(source, str):
        file_obj = open(source, newline="", encoding="utf-8-sig")
        owns_file = True
    else:
        file_obj = source
        owns_file = False

    try:
        reader = csv.DictReader(file_obj)
        # Fieldnames are populated after reading header
        first_rows = list(reader)  # read all rows to get fieldnames
        fieldnames = set(reader.fieldnames or [])

        missing = required_cols - fieldnames
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        count = 0

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            for row in first_rows:
                ticker_local = (row.get("Trading Symbol") or "").strip()
                if not ticker_local:
                    continue

                exchange = (row.get("Exchange") or "NSE").strip()
                isin = (row.get("ISIN") or "").strip() or None
                name = (row.get("Name") or row.get("Security name") or "").strip() or None

                # Parse numeric fields
                raw_qty = (row.get("Quantity") or "0").strip()
                raw_price = (row.get("Average Price") or "0").strip()

                # Cash detection: CASHCOMPONENT or zero/empty quantity
                asset_type = _classify_asset_type(ticker_local, name or "")

                if asset_type == "cash":
                    units = 0.0
                    cost_per_unit = 0.0
                    region = "india"
                    ticker_yfinance = ticker_local  # no suffix for cash
                else:
                    try:
                        units = _clean_numeric(raw_qty)
                        cost_per_unit = _clean_numeric(raw_price)
                    except ValueError:
                        continue

                    # Skip zero-quantity non-cash rows
                    if units == 0 and asset_type != "cash":
                        continue

                    region, ticker_yfinance = _map_zerodha_exchange(exchange, ticker_local)

                # Insert or replace (ISIN is unique key if present)
                cursor.execute("""
                    INSERT OR REPLACE INTO holdings
                        (broker, ticker_local, isin, ticker_yfinance, name, units,
                         cost_per_unit, currency, region, asset_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "zerodha",
                    ticker_local,
                    isin,
                    ticker_yfinance,
                    name,
                    units,
                    cost_per_unit,
                    "INR",
                    region,
                    asset_type,
                ))
                count += 1

            conn.commit()
        return count

    finally:
        if owns_file:
            file_obj.close()


# ---------------------------------------------------------------------------
# Public function 2: import_trade_republic_csv
# ---------------------------------------------------------------------------

def import_trade_republic_csv(source: Union[str, IO], db_path: str) -> int:
    """
    Parse a Trade Republic CSV (file path or file-like) and insert holdings.

    Required columns: Date, Type, ISIN, Quantity, Price per Unit
    Aggregates Buy/Sell rows by ISIN (weighted avg cost basis).
    Skips ISINs with total_units <= 0 (fully sold positions).

    Returns: count of rows inserted.
    Raises: ValueError if required columns are missing.
    """
    required_cols = {"Date", "Type", "ISIN", "Quantity", "Price per Unit"}

    if isinstance(source, str):
        file_obj = open(source, newline="", encoding="utf-8-sig")
        owns_file = True
    else:
        file_obj = source
        owns_file = False

    try:
        reader = csv.DictReader(file_obj)
        all_rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

        missing = required_cols - fieldnames
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        # Aggregate by ISIN: {isin: {total_units, total_cost, name}}
        aggregated: dict[str, dict] = {}

        for row in all_rows:
            tx_type = (row.get("Type") or "").strip().lower()
            if tx_type not in ("buy", "sell"):
                continue

            isin = (row.get("ISIN") or "").strip()
            if not isin:
                continue

            name = (row.get("Security name") or "").strip()

            try:
                qty = _clean_numeric(row.get("Quantity") or "0")
                price = _clean_numeric(row.get("Price per Unit") or "0")
            except ValueError:
                continue

            if isin not in aggregated:
                aggregated[isin] = {"total_units": 0.0, "total_cost": 0.0, "name": name}

            if tx_type == "buy":
                aggregated[isin]["total_units"] += qty
                aggregated[isin]["total_cost"] += qty * price
            else:  # sell
                aggregated[isin]["total_units"] -= qty
                aggregated[isin]["total_cost"] -= qty * price

        count = 0

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            for isin, agg in aggregated.items():
                total_units = agg["total_units"]
                total_cost = agg["total_cost"]
                name = agg["name"]

                if total_units <= 0:
                    continue  # fully sold

                if total_cost < 0:
                    logger.warning(
                        "Negative total_cost for ISIN %s — skipping (data integrity issue)", isin
                    )
                    continue

                cost_per_unit = total_cost / total_units
                asset_type = "etf" if "etf" in name.lower() else "equity"
                region = _classify_tr_region(isin)

                cursor.execute("""
                    INSERT OR REPLACE INTO holdings
                        (broker, ticker_local, isin, ticker_yfinance, name, units,
                         cost_per_unit, currency, region, asset_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "trade_republic",
                    isin,          # use ISIN as ticker_local for TR (no exchange ticker)
                    isin,
                    None,          # ticker_yfinance mapped in Plan 03 via ISIN lookup
                    name or None,
                    round(total_units, 6),
                    round(cost_per_unit, 6),
                    "EUR",
                    region,
                    asset_type,
                ))
                count += 1

            conn.commit()
        return count

    finally:
        if owns_file:
            file_obj.close()


# ---------------------------------------------------------------------------
# Public function 3: get_portfolio_with_pl
# ---------------------------------------------------------------------------

def get_portfolio_with_pl(db_path: str, fx_rate_eurinr: float = 90.0) -> dict:
    """
    Query holdings LEFT JOIN latest price_history, compute P&L per holding.

    Returns:
        {
            "holdings": [
                {
                    "id": int, "ticker": str, "isin": str|None, "name": str|None,
                    "quantity": float, "avg_buy": float, "current_price": float|None,
                    "pl": float, "pl_pct": float,
                    "pl_inr": float,
                    "currency": str, "region": str|None, "asset_type": str|None,
                    "broker": str, "price_date": str|None
                },
                ...
            ],
            "total_inr": float,
            "total_eur": float,
            "cash_by_broker": {"zerodha": float, "trade_republic": float},
        }
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            h.id,
            h.broker,
            h.ticker_local,
            h.isin,
            h.name,
            h.units,
            h.cost_per_unit,
            h.currency,
            h.region,
            h.asset_type,
            p.close  AS current_price,
            p.date   AS price_date
        FROM holdings h
        LEFT JOIN price_history p ON h.ticker_yfinance = p.ticker
            AND p.date = (
                SELECT MAX(date) FROM price_history
                WHERE ticker = h.ticker_yfinance
            )
        ORDER BY h.broker, h.region
    """)

    rows = cursor.fetchall()
    conn.close()

    holdings = []
    total_inr = 0.0
    total_eur = 0.0
    cash_by_broker: dict[str, float] = {"zerodha": 0.0, "trade_republic": 0.0}

    for row in rows:
        cost = row["cost_per_unit"]
        units = row["units"]
        current_price = row["current_price"]  # may be None

        if row["asset_type"] == "cash":
            # Cash rows: no P&L, just accumulate cash balance
            cash_value = units if units else 0.0
            broker_key = row["broker"]
            if broker_key in cash_by_broker:
                cash_by_broker[broker_key] += cash_value
            holdings.append({
                "id": row["id"],
                "ticker": row["ticker_local"],
                "isin": row["isin"],
                "name": row["name"],
                "quantity": units,
                "avg_buy": cost,
                "current_price": None,
                "pl": 0.0,
                "pl_pct": 0.0,
                "pl_inr": 0.0,
                "currency": row["currency"],
                "region": row["region"],
                "asset_type": row["asset_type"],
                "broker": row["broker"],
                "price_date": None,
            })
            continue

        # P&L calculation
        if current_price is not None:
            pl = round((current_price - cost) * units, 2)
        else:
            pl = 0.0

        pl_pct = round((pl / (cost * units) * 100) if (cost and units) else 0.0, 2)

        # Convert P&L to INR equivalent
        if row["currency"] == "EUR":
            pl_inr = round(pl * fx_rate_eurinr, 2)
        else:
            pl_inr = pl

        holdings.append({
            "id": row["id"],
            "ticker": row["ticker_local"],
            "isin": row["isin"],
            "name": row["name"],
            "quantity": units,
            "avg_buy": cost,
            "current_price": current_price,
            "pl": pl,
            "pl_pct": pl_pct,
            "pl_inr": pl_inr,
            "currency": row["currency"],
            "region": row["region"],
            "asset_type": row["asset_type"],
            "broker": row["broker"],
            "price_date": row["price_date"],
        })

        # Accumulate totals — use market value (not P&L delta)
        market_value = (current_price if current_price is not None else cost) * units
        if row["currency"] == "EUR":
            total_eur += market_value
        else:
            total_inr += market_value

    return {
        "holdings": holdings,
        "total_inr": round(total_inr, 2),
        "total_eur": round(total_eur, 2),
        "cash_by_broker": cash_by_broker,
    }
