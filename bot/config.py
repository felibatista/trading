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
class Config:
    exchange: str = "okx"
    timeframe: str = "1h"
    symbols: list[str] = field(default_factory=lambda: ["BTC/USDT"])
    strategy: StrategyParams = field(default_factory=StrategyParams)


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    strat = data.get("strategy") or {}
    return Config(
        exchange=data.get("exchange", "okx"),
        timeframe=data.get("timeframe", "1h"),
        symbols=data.get("symbols", ["BTC/USDT"]),
        strategy=StrategyParams(
            fast=strat.get("fast", 20),
            slow=strat.get("slow", 50),
            rsi_period=strat.get("rsi_period", 14),
            rsi_oversold=strat.get("rsi_oversold", 35.0),
            rsi_overbought=strat.get("rsi_overbought", 70.0),
        ),
    )
