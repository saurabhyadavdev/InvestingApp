"""
Pydantic v2 response models for InvestIQ API.
"""
from typing import List, Optional
from pydantic import BaseModel


class HoldingResponse(BaseModel):
    id: Optional[int] = None
    ticker: str
    isin: Optional[str] = None
    name: Optional[str] = None
    quantity: float
    avg_buy: float
    current_price: float
    pl: float
    pl_pct: float
    currency: str
    region: Optional[str] = None
    asset_type: Optional[str] = None
    broker: str
    price_date: Optional[str] = None


class PortfolioResponse(BaseModel):
    holdings: List[HoldingResponse]
    total_inr: float
    total_eur: float
    updated_at: str
