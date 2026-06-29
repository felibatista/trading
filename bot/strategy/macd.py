from __future__ import annotations

import pandas as pd

from bot.indicators import macd
from bot.models import Action, Signal


def decide_macd(df: pd.DataFrame, params: dict) -> Signal:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal_p = params.get("signal", 9)
    line, signal_line, hist = macd(df["close"], fast, slow, signal_p)
    ind = {
        "macd": float(line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "hist": float(hist.iloc[-1]),
    }
    prev, curr = float(hist.iloc[-2]), float(hist.iloc[-1])
    if prev <= 0 < curr:
        return Signal(Action.BUY, f"MACD cruzó al alza (hist {curr:.4f})", ind)
    if prev >= 0 > curr:
        return Signal(Action.SELL, f"MACD cruzó a la baja (hist {curr:.4f})", ind)
    return Signal(Action.HOLD, "MACD sin cruce", ind)
