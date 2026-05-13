"""
Portfolio endpoints:
  - POST /api/import  — accept Zerodha or Trade Republic CSV, import to SQLite
  - GET  /api/portfolio — return holdings with P&L and cash_by_broker

All SQL uses parameterized queries (? placeholders) — no f-string interpolation.
"""
import tempfile
import os
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from backend.config import settings
from backend.models import HoldingResponse, ImportResponse, PortfolioResponse
from backend.core.portfolio import (
    import_zerodha_csv,
    import_trade_republic_csv,
    get_portfolio_with_pl,
)

router = APIRouter(prefix="/api")

VALID_BROKERS = ("zerodha", "trade_republic")


@router.post("/import", response_model=ImportResponse)
async def import_portfolio(
    broker: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accept a CSV file upload for a specific broker and import holdings to SQLite.

    Form fields:
        broker: "zerodha" or "trade_republic"
        file: CSV file content

    Returns ImportResponse with imported_count.
    Raises:
        400 if broker is not in the valid list.
        422 if CSV is missing required columns.
    """
    if broker not in VALID_BROKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid broker '{broker}'. Must be one of: {', '.join(VALID_BROKERS)}",
        )

    # Save uploaded file to a temp location, then parse it
    content = await file.read()

    # Write to temp file so csv.DictReader can open by path, OR pass as StringIO
    # We use io.StringIO to avoid temp file cleanup complexity
    import io
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    csv_io = io.StringIO(text)

    try:
        if broker == "zerodha":
            count = import_zerodha_csv(csv_io, settings.DB_PATH)
        else:
            count = import_trade_republic_csv(csv_io, settings.DB_PATH)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ImportResponse(
        broker=broker,
        imported_count=count,
        message="Import successful",
    )


def _get_cached_fx_rate(db_path: str, fallback: float = 90.0) -> float:
    """Read the latest EUR/INR rate from the fx_rates table; fall back to default if unavailable."""
    import sqlite3 as _sqlite3
    try:
        conn = _sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT rate FROM fx_rates ORDER BY timestamp DESC LIMIT 1")
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
    Return all holdings with current price and P&L.
    Uses the latest cached EUR/INR rate from fx_rates table; falls back to 90.0 if not cached.
    """
    fx_rate = _get_cached_fx_rate(settings.DB_PATH)
    result = get_portfolio_with_pl(settings.DB_PATH, fx_rate_eurinr=fx_rate)

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
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        cash_by_broker=result["cash_by_broker"],
    )
