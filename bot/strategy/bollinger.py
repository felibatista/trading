from __future__ import annotations

import math

import pandas as pd

from bot.indicators import bollinger
from bot.models import Action, Signal


def decide_bollinger(df: pd.DataFrame, params: dict) -> Signal:
    period = params.get("period", 20)
    num_std = params.get("num_std", 2.0)
    mid, upper, lower = bollinger(df["close"], period, num_std)
    lower_ref = lower.shift(1)  # banda PREVIA (no incluye la vela que pinchó)
    upper_ref = upper.shift(1)
    ind = {
        "bb_mid": float(mid.iloc[-1]),
        "bb_upper": float(upper.iloc[-1]),
        "bb_lower": float(lower.iloc[-1]),
    }
    c_prev, c_now = float(df["close"].iloc[-2]), float(df["close"].iloc[-1])
    lo_ref = float(lower_ref.iloc[-2])
    up_ref = float(upper_ref.iloc[-2])
    if math.isnan(lo_ref) or math.isnan(up_ref):
        return Signal(Action.HOLD, "Bollinger sin datos suficientes", ind)
    if c_prev < lo_ref and c_now > c_prev:
        return Signal(Action.BUY, "Rebote desde la banda inferior", ind)
    if c_prev > up_ref and c_now < c_prev:
        return Signal(Action.SELL, "Reversión desde la banda superior", ind)
    return Signal(Action.HOLD, "Dentro de las bandas", ind)
