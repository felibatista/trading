from __future__ import annotations

import pandas as pd

from bot.models import Action, Signal


def decide_price_action(df: pd.DataFrame, params: dict) -> Signal:
    wick_ratio = params.get("wick_ratio", 2.0)
    o = float(df["open"].iloc[-1]); h = float(df["high"].iloc[-1])
    low = float(df["low"].iloc[-1]); c = float(df["close"].iloc[-1])
    po = float(df["open"].iloc[-2]); pc = float(df["close"].iloc[-2])

    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - low
    ind = {"body": body, "upper_wick": upper_wick, "lower_wick": lower_wick}

    # Engulfing (tiene prioridad sobre las mechas).
    if pc < po and c > o and o <= pc and c >= po:
        return Signal(Action.BUY, "Envolvente alcista", ind)
    if pc > po and c < o and o >= pc and c <= po:
        return Signal(Action.SELL, "Envolvente bajista", ind)

    # Mechas (martillo / estrella fugaz). Requiere cuerpo no nulo.
    if body > 0:
        if lower_wick >= wick_ratio * body and upper_wick <= body:
            return Signal(Action.BUY, "Martillo (mecha inferior larga)", ind)
        if upper_wick >= wick_ratio * body and lower_wick <= body:
            return Signal(Action.SELL, "Estrella fugaz (mecha superior larga)", ind)

    return Signal(Action.HOLD, "Sin patrón de price action", ind)
