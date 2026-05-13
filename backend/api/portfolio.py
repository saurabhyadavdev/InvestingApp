"""
Portfolio endpoint — reads holdings from SQLite and returns P&L.
All SQL uses parameterized queries (? placeholders) — no f-string interpolation.
"""
import sqlite3
from datetime import datetime
from typing import List
from fastapi import APIRouter

from backend.config import settings
from backend.models import HoldingResponse, PortfolioResponse

router = APIRouter(prefix="/api")


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """
    Return all holdings with current price and P&L.
    Reads from holdings LEFT JOIN price_history (most recent date per ticker).
    """
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Parameterized query only — no f-string SQL interpolation
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

    holdings: List[HoldingResponse] = []
    total_inr = 0.0
    total_eur = 0.0

    for row in rows:
        current_price = row["current_price"] if row["current_price"] is not None else 0.0
        cost = row["cost_per_unit"]
        units = row["units"]

        pl = round((current_price - cost) * units, 2)
        pl_pct = round((pl / (cost * units) * 100) if cost and units else 0.0, 2)

        holdings.append(HoldingResponse(
            id=row["id"],
            ticker=row["ticker_local"],
            isin=row["isin"],
            name=row["name"],
            quantity=units,
            avg_buy=cost,
            current_price=current_price,
            pl=pl,
            pl_pct=pl_pct,
            currency=row["currency"],
            region=row["region"],
            asset_type=row["asset_type"],
            broker=row["broker"],
            price_date=row["price_date"],
        ))

        # Accumulate totals by currency (simplified: separate INR and EUR buckets)
        value = current_price * units if current_price else cost * units
        if row["currency"] == "EUR":
            total_eur += value
        else:
            total_inr += value

    return PortfolioResponse(
        holdings=holdings,
        total_inr=round(total_inr, 2),
        total_eur=round(total_eur, 2),
        updated_at=datetime.utcnow().isoformat(),
    )
