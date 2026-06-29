from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.price_action import decide_price_action


def _df(rows):
    # rows: lista de (open, high, low, close)
    n = len(rows)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": [r[0] for r in rows], "high": [r[1] for r in rows],
        "low": [r[2] for r in rows], "close": [r[3] for r in rows], "volume": [1] * n,
    })


def test_bullish_engulfing_buys():
    rows = [(10, 10.5, 9.5, 10), (10, 10.2, 8, 9), (9, 12, 8.9, 11.5)]
    # prev: bajista (open 10 -> close 9); curr: alcista que envuelve (open 9 <= 9, close 11.5 >= 10)
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.BUY


def test_bearish_engulfing_sells():
    rows = [(10, 10.5, 9.5, 10), (9, 11, 8.9, 10.5), (11, 11.2, 8.5, 9)]
    # prev: alcista (9 -> 10.5); curr: bajista que envuelve (open 11 >= 10.5, close 9 <= 9)
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.SELL


def test_hammer_buys():
    rows = [(10, 10.5, 9.5, 10), (10, 10.2, 9.8, 10.1)]
    # última: martillo (cuerpo 0.1, mecha inferior 10.0-... ). Construido para gatillar BUY.
    rows[-1] = (10.0, 10.1, 9.0, 10.05)  # cuerpo 0.05, mecha inf 1.0 (>= 2x cuerpo), mecha sup 0.05
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.BUY


def test_doji_inside_holds():
    rows = [(10, 10.5, 9.5, 10), (10, 10.6, 9.4, 10.1)]
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.HOLD
