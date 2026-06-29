from __future__ import annotations

from bot.config import StrategyParams
from bot.models import Signal
from bot.strategy.base import StrategyFn
from bot.strategy.ema_rsi import evaluate
from bot.strategy.bollinger import decide_bollinger
from bot.strategy.breakout import decide_breakout
from bot.strategy.macd import decide_macd
from bot.strategy.price_action import decide_price_action


def decide_ema_rsi(df, params: dict) -> Signal:
    sp = StrategyParams(
        fast=params.get("fast", 20),
        slow=params.get("slow", 50),
        rsi_period=params.get("rsi_period", 14),
        rsi_oversold=params.get("rsi_oversold", 35.0),
        rsi_overbought=params.get("rsi_overbought", 70.0),
    )
    return evaluate(df, sp)


STRATEGIES: dict[str, StrategyFn] = {
    "ema_rsi": decide_ema_rsi,
    "macd": decide_macd,
    "bollinger": decide_bollinger,
    "breakout": decide_breakout,
    "price_action": decide_price_action,
}


def get_strategy(name: str) -> StrategyFn:
    if name not in STRATEGIES:
        raise KeyError(
            f"Estrategia desconocida: {name!r}. Disponibles: {sorted(STRATEGIES)}"
        )
    return STRATEGIES[name]


def available() -> list[str]:
    return sorted(STRATEGIES)
