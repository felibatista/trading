from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class StrategyParams:
    fast: int = 20
    slow: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 70.0


@dataclass
class BrokerParams:
    kind: str = "paper"  # "paper" | "okx_demo"
    paper_cash: float = 10000.0
    fee_rate: float = 0.001
    slippage: float = 0.0005


@dataclass
class RiskParams:
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_exposure_pct: float = 0.30
    max_positions: int = 3


@dataclass
class AIParams:
    # Apagada por defecto en el código (seguro); config.yaml puede prenderla.
    enabled: bool = False
    # Default de semilla y del path CLI; en la flota, cada cuenta elige proveedor/modelo.
    provider: str = "anthropic"  # "anthropic" | "openai"
    model: str = "claude-haiku-4-5"  # configurable a claude-sonnet-4-6 / claude-opus-4-8
    timeout_seconds: float = 20.0
    max_retries: int = 1


@dataclass
class Config:
    exchange: str = "okx"
    timeframe: str = "1h"
    symbols: list[str] = field(default_factory=lambda: ["BTC/USDT"])
    limit: int = 200
    db_path: str = "americo.sqlite"
    loop_interval_seconds: int = 3600
    strategy: StrategyParams = field(default_factory=StrategyParams)
    broker: BrokerParams = field(default_factory=BrokerParams)
    risk: RiskParams = field(default_factory=RiskParams)
    ai: AIParams = field(default_factory=AIParams)


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    strat = data.get("strategy") or {}
    brk = data.get("broker") or {}
    rsk = data.get("risk") or {}
    ai = data.get("ai") or {}
    return Config(
        exchange=data.get("exchange", "okx"),
        timeframe=data.get("timeframe", "1h"),
        symbols=data.get("symbols", ["BTC/USDT"]),
        limit=data.get("limit", 200),
        db_path=data.get("db_path", "americo.sqlite"),
        loop_interval_seconds=data.get("loop_interval_seconds", 3600),
        strategy=StrategyParams(
            fast=strat.get("fast", 20),
            slow=strat.get("slow", 50),
            rsi_period=strat.get("rsi_period", 14),
            rsi_oversold=strat.get("rsi_oversold", 35.0),
            rsi_overbought=strat.get("rsi_overbought", 70.0),
        ),
        broker=BrokerParams(
            kind=brk.get("kind", "paper"),
            paper_cash=brk.get("paper_cash", 10000.0),
            fee_rate=brk.get("fee_rate", 0.001),
            slippage=brk.get("slippage", 0.0005),
        ),
        risk=RiskParams(
            risk_per_trade=rsk.get("risk_per_trade", 0.01),
            stop_loss_pct=rsk.get("stop_loss_pct", 0.02),
            take_profit_pct=rsk.get("take_profit_pct", 0.04),
            max_exposure_pct=rsk.get("max_exposure_pct", 0.30),
            max_positions=rsk.get("max_positions", 3),
        ),
        ai=AIParams(
            enabled=ai.get("enabled", False),
            provider=ai.get("provider", "anthropic"),
            model=ai.get("model", "claude-haiku-4-5"),
            timeout_seconds=ai.get("timeout_seconds", 20.0),
            max_retries=ai.get("max_retries", 1),
        ),
    )
