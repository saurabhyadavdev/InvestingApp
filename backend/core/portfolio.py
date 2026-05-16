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
from typing import Optional, Union, IO

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public function 0: compute_daily_pct
# ---------------------------------------------------------------------------

def compute_daily_pct(db_path: str, ticker: str) -> Optional[float]:
    """
    Compute the daily % change for a ticker from the two most recent rows
    in price_history.

    Returns (close_today - close_prev) / close_prev * 100 when exactly two
    rows are available and the previous close is non-zero.
    Returns None in all other cases (single row, zero rows, zero prev close,
    or missing ticker).

    Security note: uses parameterized ? placeholders — no f-string SQL.
    """
    if not ticker:
        return None
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT close FROM price_history WHERE ticker = ? ORDER BY date DESC LIMIT 2",
            (ticker,),
        ).fetchall()
        if len(rows) == 2 and rows[1][0] and rows[1][0] != 0:
            return (rows[0][0] - rows[1][0]) / rows[1][0] * 100
        return None
    except Exception:
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_numeric(value: str) -> float:
    """Strip currency symbols, commas, and whitespace from a string and parse as float."""
    cleaned = value.replace("₹", "").replace(",", "").replace(" ", "").strip()
    if not cleaned or cleaned in ("-", "--", "N/A", "n/a", "NA"):
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

    Supports two Zerodha export formats:
    - Holdings export: Trading Symbol, Quantity, Average Price, ISIN
    - Kite portfolio view: Instrument, Qty., Avg. cost, LTP

    Returns: count of rows inserted.
    Raises: ValueError if required columns are missing.
    """
    # Column aliases: Kite portfolio view → canonical names
    _COL_ALIASES = {
        "Instrument": "Trading Symbol",
        "Qty.": "Quantity",
        "Avg. cost": "Average Price",
    }
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

        # Remap rows if Kite portfolio view columns detected
        if _COL_ALIASES.keys() & fieldnames:
            first_rows = [
                {_COL_ALIASES.get(k, k): v for k, v in row.items()}
                for row in first_rows
            ]
            fieldnames = {_COL_ALIASES.get(f, f) for f in fieldnames}

        missing = required_cols - fieldnames
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        count = 0

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Clear existing Zerodha holdings so re-imports replace rather than append
            cursor.execute("DELETE FROM holdings WHERE broker = 'zerodha'")

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

    Supports two TR export formats:
      Legacy: Date, Type, ISIN, Quantity, Price per Unit, Security name
      New:    datetime/date, type, symbol, shares, price, name, asset_class, category

    Aggregates buy/sell rows by ISIN/symbol (weighted avg cost basis).
    Skips positions with total_units <= 0 (fully sold).

    Returns: count of rows inserted.
    Raises: ValueError if required columns are missing from both formats.
    """
    # Column map: lowercase CSV header → internal field name.
    # 'type' takes priority over 'category' — both can map to "Type" but 'type' is explicit.
    _TR_ALIASES = {
        "datetime": "Date",
        "date": "Date",
        "symbol": "ISIN",         # new format uses symbol (contains ISIN value)
        "isin": "ISIN",
        "shares": "Quantity",
        "quantity": "Quantity",
        "price": "Price per Unit",
        "price per unit": "Price per Unit",
        "name": "Security name",
    }
    required_cols = {"Date", "ISIN", "Quantity", "Price per Unit"}

    if isinstance(source, str):
        file_obj = open(source, newline="", encoding="utf-8-sig")
        owns_file = True
    else:
        file_obj = source
        owns_file = False

    try:
        reader = csv.DictReader(file_obj)
        all_rows = list(reader)
        # Preserve column order so priority resolution is deterministic
        raw_fieldnames = list(reader.fieldnames or [])
        raw_lower = {f.strip().lower(): f for f in raw_fieldnames}

        def _get(row, internal):
            """Get value by internal field name using the alias map."""
            for alias, mapped in _TR_ALIASES.items():
                if mapped == internal and alias in raw_lower:
                    val = row.get(raw_lower[alias])
                    if val is not None:
                        return val
            return None

        # Detect which column carries buy/sell type info.
        # New format: 'type' column has "BUY"/"SELL"; 'category' has "TRADING"/"CASH".
        # Legacy format: 'Type' column has "Buy"/"Sell".
        type_col = raw_lower.get("type") or raw_lower.get("Type")

        mapped_fieldnames = {_TR_ALIASES[a] for a in _TR_ALIASES if a in raw_lower}
        missing = required_cols - mapped_fieldnames
        if missing or not type_col:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing or {'Type'}))}")

        # Detect new format: 'symbol' column present (contains ISIN values)
        new_format = "symbol" in raw_lower

        # Aggregate by ISIN/symbol: {key: {total_units, buy_cost, buy_units, name}}
        aggregated: dict[str, dict] = {}

        for row in all_rows:
            # Read transaction type directly from the resolved type column
            tx_type = (row.get(type_col) or "").strip().upper()

            # Accept BUY / SELL / SAVINGS_PLAN (savings plan = recurring buy)
            if tx_type not in ("BUY", "SELL", "SAVINGS_PLAN"):
                continue
            is_buy = tx_type in ("BUY", "SAVINGS_PLAN")

            isin = (_get(row, "ISIN") or "").strip()
            if not isin:
                continue

            name = (_get(row, "Security name") or "").strip()
            asset_class = (row.get("asset_class") or "").strip().lower() if new_format else ""

            try:
                qty = _clean_numeric(_get(row, "Quantity") or "0")
                price = _clean_numeric(_get(row, "Price per Unit") or "0")
            except ValueError:
                continue

            if isin not in aggregated:
                aggregated[isin] = {"total_units": 0.0, "buy_cost": 0.0, "buy_units": 0.0, "name": name, "asset_class": asset_class}

            if is_buy:
                aggregated[isin]["total_units"] += qty
                aggregated[isin]["buy_units"] += qty
                aggregated[isin]["buy_cost"] += qty * price
            else:  # sell — only reduce net units, never touch buy_cost
                aggregated[isin]["total_units"] -= qty

        count = 0

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Clear existing TR holdings so re-imports replace rather than append
            cursor.execute("DELETE FROM holdings WHERE broker = 'trade_republic'")

            for isin, agg in aggregated.items():
                total_units = agg["total_units"]
                buy_cost = agg["buy_cost"]
                buy_units = agg["buy_units"]
                name = agg["name"]

                if total_units <= 0:
                    continue  # fully sold

                if buy_cost < 0:
                    logger.warning(
                        "Negative buy_cost for ISIN %s — skipping (data integrity issue)", isin
                    )
                    continue

                cost_per_unit = buy_cost / buy_units if buy_units > 0 else 0.0
                region = _classify_tr_region(isin)
                # New format provides asset_class directly; fall back to name/region heuristic
                agg_asset_class = agg.get("asset_class", "")
                if agg_asset_class in ("fund", "etf"):
                    asset_type = "etf"
                elif "etf" in name.lower() or region == "etf":
                    asset_type = "etf"
                else:
                    asset_type = "equity"

                # In new format, symbol is the ticker (e.g. "AAPL"), not ISIN.
                # Store symbol as ticker_local; isin column gets the value too for backward compat.
                ticker_local = agg.get("symbol") or isin

                cursor.execute("""
                    INSERT OR REPLACE INTO holdings
                        (broker, ticker_local, isin, ticker_yfinance, name, units,
                         cost_per_unit, currency, region, asset_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "trade_republic",
                    ticker_local,
                    isin,          # isin may equal symbol in new format — still stored
                    None,          # ticker_yfinance mapped later via ISIN lookup
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

def get_portfolio_with_pl(
    db_path: str,
    fx_rate_eurinr: float = 90.0,
    fx_rate_usdinr: float = 83.0,
) -> dict:
    """
    Query holdings LEFT JOIN latest price_history, compute P&L per holding.

    Args:
        db_path: Path to SQLite database.
        fx_rate_eurinr: EUR/INR conversion rate (default 90.0).
        fx_rate_usdinr: USD/INR conversion rate (default 83.0). Used to compute pl_usd.

    Returns:
        {
            "holdings": [
                {
                    "id": int, "ticker": str, "ticker_yfinance": str|None,
                    "isin": str|None, "name": str|None,
                    "quantity": float, "avg_buy": float, "current_price": float|None,
                    "pl": float, "pl_pct": float,
                    "pl_inr": float, "pl_usd": float,
                    "currency": str, "region": str|None, "asset_type": str|None,
                    "broker": str, "price_date": str|None
                },
                ...
            ],
            "total_inr": float,
            "total_eur": float,
            "total_usd": float,
            "cash_by_broker": {"zerodha": float, "trade_republic": float},
        }
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                h.id,
                h.broker,
                h.ticker_local,
                h.ticker_yfinance,
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
    finally:
        conn.close()

    holdings = []
    total_inr = 0.0
    total_eur = 0.0
    total_usd = 0.0
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
                "ticker_yfinance": row["ticker_yfinance"],
                "isin": row["isin"],
                "name": row["name"],
                "quantity": units,
                "avg_buy": cost,
                "current_price": None,
                "pl": 0.0,
                "pl_pct": 0.0,
                "pl_inr": 0.0,
                "pl_usd": 0.0,
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

        # Convert P&L to USD equivalent (T-05-01: rate from trusted source only, never user input)
        if row["currency"] == "EUR":
            pl_usd = round(pl * fx_rate_eurinr / fx_rate_usdinr, 2)
        else:
            # INR or any other currency: divide by USDINR rate
            pl_usd = round(pl / fx_rate_usdinr, 2)

        holdings.append({
            "id": row["id"],
            "ticker": row["ticker_local"],
            "ticker_yfinance": row["ticker_yfinance"],
            "isin": row["isin"],
            "name": row["name"],
            "quantity": units,
            "avg_buy": cost,
            "current_price": current_price,
            "pl": pl,
            "pl_pct": pl_pct,
            "pl_inr": pl_inr,
            "pl_usd": pl_usd,
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
            total_usd += market_value * fx_rate_eurinr / fx_rate_usdinr
        else:
            total_inr += market_value
            total_usd += market_value / fx_rate_usdinr

    has_live_prices = any(h.get("price_date") for h in holdings)
    return {
        "holdings": holdings,
        "total_inr": round(total_inr, 2),
        "total_eur": round(total_eur, 2),
        "total_usd": round(total_usd, 2),
        "cash_by_broker": cash_by_broker,
        "total_basis": "market" if has_live_prices else "cost",
    }
