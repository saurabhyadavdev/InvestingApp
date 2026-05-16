"""
Portfolio endpoints:
  - POST /api/import  — accept Zerodha/Trade Republic CSV or Traders Place PDF
  - GET  /api/portfolio — return holdings with P&L and cash_by_broker

All SQL uses parameterized queries (? placeholders) — no f-string interpolation.
"""
import io
import sqlite3 as _sqlite3
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from backend.config import settings
from backend.models import HoldingResponse, ImportResponse, PortfolioResponse
from backend.core.portfolio import (
    import_zerodha_csv,
    import_trade_republic_csv,
    import_traders_place_pdf,
    resolve_tr_yfinance_tickers,
    get_portfolio_with_pl,
)
from backend.core.data_fetcher import DataFetcher

router = APIRouter(prefix="/api")

VALID_BROKERS = ("zerodha", "trade_republic", "traders_place")


def _fetch_resolved_prices(db_path: str, broker: str) -> None:
    """Fetch latest prices for all resolved holdings of a broker (best-effort)."""
    conn = _sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT ticker_yfinance FROM holdings "
            "WHERE broker=? AND ticker_yfinance IS NOT NULL",
            (broker,),
        ).fetchall()
    finally:
        conn.close()

    tickers = [r[0] for r in rows if r[0]]
    if tickers:
        DataFetcher(db_path).fetch_holding_prices(tickers)


@router.post("/import", response_model=ImportResponse)
async def import_portfolio(
    broker: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accept a file upload for a specific broker and import holdings to SQLite.

    Form fields:
        broker: "zerodha", "trade_republic", or "traders_place"
        file: CSV (Zerodha/TR) or PDF (Traders Place quarterly statement)

    Returns ImportResponse with imported_count.
    """
    if broker not in VALID_BROKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid broker '{broker}'. Must be one of: {', '.join(VALID_BROKERS)}",
        )

    content = await file.read()

    try:
        if broker == "zerodha":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("latin-1")
            count = import_zerodha_csv(io.StringIO(text), settings.DB_PATH)

        elif broker == "trade_republic":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = content.decode("latin-1")
            count = import_trade_republic_csv(io.StringIO(text), settings.DB_PATH)
            try:
                resolve_tr_yfinance_tickers(settings.DB_PATH)
                _fetch_resolved_prices(settings.DB_PATH, "trade_republic")
            except Exception:
                pass

        else:  # traders_place — PDF
            count = import_traders_place_pdf(content, settings.DB_PATH)
            try:
                resolve_tr_yfinance_tickers(settings.DB_PATH)
                _fetch_resolved_prices(settings.DB_PATH, "traders_place")
            except Exception:
                pass

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ImportResponse(
        broker=broker,
        imported_count=count,
        message="Import successful",
    )


def _get_cached_fx_rate(db_path: str, fallback: float = 90.0) -> float:
    """Read the latest EUR/INR rate from the fx_rates table; fall back to default if unavailable."""
    try:
        conn = _sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rate FROM fx_rates WHERE pair = 'EURINR' ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return float(row[0])
        finally:
            conn.close()
    except Exception:
        pass
    return fallback


def _get_cached_usdinr_rate(db_path: str, fallback: float = 83.0) -> float:
    """Read the latest USD/INR rate from the fx_rates table (pair='USDINR'); fall back to 83.0."""
    try:
        conn = _sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rate FROM fx_rates WHERE pair='USDINR' ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return float(row[0])
        finally:
            conn.close()
    except Exception:
        pass
    return fallback


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """
    Return all holdings with current price and P&L including USD totals.
    Uses the latest cached EUR/INR and USD/INR rates from fx_rates table;
    falls back to 90.0 / 83.0 respectively if not cached.
    """
    fx_rate_eurinr = _get_cached_fx_rate(settings.DB_PATH)
    fx_rate_usdinr = _get_cached_usdinr_rate(settings.DB_PATH)
    result = get_portfolio_with_pl(
        settings.DB_PATH,
        fx_rate_eurinr=fx_rate_eurinr,
        fx_rate_usdinr=fx_rate_usdinr,
    )

    holdings: List[HoldingResponse] = []
    for h in result["holdings"]:
        holdings.append(HoldingResponse(
            id=h.get("id"),
            ticker=h["ticker"],
            isin=h.get("isin"),
            name=h.get("name"),
            quantity=h["quantity"],
            avg_buy=h["avg_buy"],
            current_price=h.get("current_price"),
            pl=h["pl"],
            pl_pct=h["pl_pct"],
            pl_usd=h.get("pl_usd", 0.0),
            currency=h["currency"],
            region=h.get("region"),
            asset_type=h.get("asset_type"),
            broker=h["broker"],
            price_date=h.get("price_date"),
        ))

    return PortfolioResponse(
        holdings=holdings,
        total_inr=result["total_inr"],
        total_eur=result["total_eur"],
        total_usd=result.get("total_usd", 0.0),
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        cash_by_broker=result["cash_by_broker"],
    )
