from __future__ import annotations

import math

import pandas as pd

from bot.models import Action, Signal


def decide_breakout(df: pd.DataFrame, params: dict) -> Signal:
    lookback = params.get("lookback", 20)
    upper = df["high"].rolling(lookback).max().shift(1)
    lower = df["low"].rolling(lookback).min().shift(1)
    up = float(upper.iloc[-1])
    lo = float(lower.iloc[-1])
    close = float(df["close"].iloc[-1])
    ind = {"donchian_upper": up, "donchian_lower": lo}
    if math.isnan(up) or math.isnan(lo):
        return Signal(Action.HOLD, "Donchian sin datos suficientes", ind)
    if close > up:
        return Signal(Action.BUY, f"Ruptura del techo Donchian ({up:.2f})", ind)
    if close < lo:
        return Signal(Action.SELL, f"Ruptura del piso Donchian ({lo:.2f})", ind)
    return Signal(Action.HOLD, "Dentro del rango Donchian", ind)
