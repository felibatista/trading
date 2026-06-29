from __future__ import annotations

from pydantic import BaseModel, Field


class StrategyOut(BaseModel):
    fast: int = 20
    slow: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 70.0


class StatusResponse(BaseModel):
    exchange: str
    timeframe: str
    broker_kind: str
    symbols: list[str]
    equity: float
    cash: float
    loop_interval_seconds: int = 3600
    last_run_at: str | None = None
    next_run_at: str | None = None
    strategy: StrategyOut = Field(default_factory=StrategyOut)


class CandleOut(BaseModel):
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float


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


class AccountOut(BaseModel):
    id: str
    name: str
    strategy: str
    symbol: str
    timeframe: str
    interval_seconds: int
    ai_enabled: bool
    enabled: bool
    starting_cash: float
    equity: float
    cash: float
