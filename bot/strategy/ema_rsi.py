from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bot.config import StrategyParams
from bot.indicators import ema, rsi
from bot.models import Action, Signal


@dataclass
class Features:
    ema_fast: float
    ema_slow: float
    ema_fast_prev: float
    ema_slow_prev: float
    rsi: float


def compute_features(df: pd.DataFrame, params: StrategyParams) -> Features:
    close = df["close"]
    ef = ema(close, params.fast)
    es = ema(close, params.slow)
    r = rsi(close, params.rsi_period)
    return Features(
        ema_fast=float(ef.iloc[-1]),
        ema_slow=float(es.iloc[-1]),
        ema_fast_prev=float(ef.iloc[-2]),
        ema_slow_prev=float(es.iloc[-2]),
        rsi=float(r.iloc[-1]),
    )


def decide(f: Features, params: StrategyParams) -> Signal:
    indicators = {"ema_fast": f.ema_fast, "ema_slow": f.ema_slow, "rsi": f.rsi}
    cross_up = f.ema_fast_prev <= f.ema_slow_prev and f.ema_fast > f.ema_slow
    cross_down = f.ema_fast_prev >= f.ema_slow_prev and f.ema_fast < f.ema_slow

    if cross_up and f.rsi < params.rsi_overbought:
        reason = f"EMA{params.fast} cruzó por encima de EMA{params.slow} (RSI {f.rsi:.0f})"
        return Signal(Action.BUY, reason, indicators)

    if cross_down or f.rsi >= params.rsi_overbought:
        reason = (
            "RSI en sobrecompra"
            if f.rsi >= params.rsi_overbought
            else f"EMA{params.fast} cruzó por debajo de EMA{params.slow}"
        )
        return Signal(Action.SELL, reason, indicators)

    return Signal(Action.HOLD, "Sin cruce de EMAs ni señal de RSI", indicators)


def evaluate(df: pd.DataFrame, params: StrategyParams) -> Signal:
    return decide(compute_features(df, params), params)
