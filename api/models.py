from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

_STRATS = {"ema_rsi", "macd", "bollinger", "breakout", "price_action"}
_TFS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"}
_PROVIDERS = {"anthropic", "openai"}


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
    ai_provider: str
    ai_model: str
    enabled: bool
    starting_cash: float
    equity: float
    cash: float


class AccountUpdate(BaseModel):
    name: str | None = None
    strategy: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    interval_seconds: int | None = Field(default=None, ge=5, le=86400)
    starting_cash: float | None = Field(default=None, gt=0)
    ai_enabled: bool | None = None
    ai_provider: str | None = None
    ai_model: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    params: dict | None = None

    @field_validator("strategy")
    @classmethod
    def _v_strategy(cls, v: str | None) -> str | None:
        if v is not None and v not in _STRATS:
            raise ValueError(f"strategy inválida: {v}")
        return v

    @field_validator("timeframe")
    @classmethod
    def _v_timeframe(cls, v: str | None) -> str | None:
        if v is not None and v not in _TFS:
            raise ValueError(f"timeframe inválido: {v}")
        return v

    @field_validator("ai_provider")
    @classmethod
    def _v_provider(cls, v: str | None) -> str | None:
        if v is not None and v not in _PROVIDERS:
            raise ValueError(f"proveedor inválido: {v}")
        return v


class BacktestRequest(BaseModel):
    # `from` es palabra reservada en Python: se acepta como alias y como from_.
    model_config = ConfigDict(populate_by_name=True)
    days: int = Field(default=7, ge=1, le=90)
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    symbol: str | None = None

    @field_validator("from_", "to")
    @classmethod
    def _v_date(cls, v: str | None) -> str | None:
        # Valida acá (→ 422 limpio) en vez de explotar en resolve_window (→ 500 crudo).
        if v is not None:
            import pandas as pd

            try:
                pd.Timestamp(v)
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"fecha inválida: {v!r}") from exc
        return v


class BacktestPoint(BaseModel):
    ts: str
    equity: float


class BacktestResultOut(BaseModel):
    account_id: str
    name: str
    strategy: str
    ai: bool
    return_pct: float
    max_drawdown_pct: float
    win_rate: float
    num_trades: int
    final_equity: float
    exposure: float
    starting_cash: float
    sharpe: float
    profit_factor: float | None = None
    equity_curve: list[BacktestPoint] = Field(default_factory=list)


class BacktestJobStatus(BaseModel):
    job_id: str
    status: str  # "running" | "done" | "error"
    results: list[BacktestResultOut] | None = None
    error: str | None = None
