"""
Pydantic v2 response models for InvestIQ API.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator


class HoldingResponse(BaseModel):
    id: Optional[int] = None
    ticker: str
    isin: Optional[str] = None
    name: Optional[str] = None
    quantity: float
    avg_buy: float
    current_price: Optional[float] = None
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
    cash_by_broker: Dict[str, float] = {}


class ImportResponse(BaseModel):
    broker: str
    imported_count: int
    message: str


# ---------------------------------------------------------------------------
# Plan 03: Market indices models
# ---------------------------------------------------------------------------

class IndexEntry(BaseModel):
    symbol: str
    name: str
    close: float
    change_pct: float
    date: str
    market_label: str


class IndicesResponse(BaseModel):
    indices: List[IndexEntry]
    fetched_at: str


# ---------------------------------------------------------------------------
# Plan 03: FX rate models
# ---------------------------------------------------------------------------

class FXResponse(BaseModel):
    pair: str
    rate: float
    low: float
    high: float
    timestamp: str
    alert_threshold: Optional[float] = None


class FXAlertRequest(BaseModel):
    threshold: float

    @field_validator("threshold")
    @classmethod
    def threshold_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("threshold must be a positive number")
        return v


class FXAlertResponse(BaseModel):
    alert_threshold: float
    message: str


# ---------------------------------------------------------------------------
# Plan 04: Briefing orchestration models
# ---------------------------------------------------------------------------

class BriefingResponse(BaseModel):
    portfolio: dict
    indices: dict
    fx: dict
    generated_at: str
    briefing_date: str
    fetched_at: str


class RefreshResponse(BaseModel):
    status: str
    generated_at: str
