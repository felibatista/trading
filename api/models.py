from __future__ import annotations

from pydantic import BaseModel


class StatusResponse(BaseModel):
    exchange: str
    timeframe: str
    broker_kind: str
    symbols: list[str]
    equity: float
    cash: float


class EquityPoint(BaseModel):
    ts: str
    equity: float
    cash: float


class PositionOut(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float


class DecisionOut(BaseModel):
    ts: str
    symbol: str
    action: str
    reason: str
    ema_fast: float
    ema_slow: float
    rsi: float
    ai_action: str | None = None
    ai_confidence: float | None = None
    ai_rationale: str | None = None


class FillOut(BaseModel):
    ts: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
