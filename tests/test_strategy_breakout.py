from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.breakout import decide_breakout


def _df(highs, lows, closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": highs, "low": lows, "close": closes, "volume": [1] * n,
    })


def test_breakout_buys_above_prior_high():
    highs = [10] * 10 + [12]      # la última rompe el techo previo (10)
    lows = [8] * 11
    closes = [9] * 10 + [11]
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.BUY


def test_breakout_sells_below_prior_low():
    highs = [10] * 11
    lows = [8] * 10 + [6]
    closes = [9] * 10 + [5]       # cierra por debajo del piso previo (8)
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.SELL


def test_breakout_holds_inside_range():
    highs = [10] * 11
    lows = [8] * 11
    closes = [9] * 11
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.HOLD
