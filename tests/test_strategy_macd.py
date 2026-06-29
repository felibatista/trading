from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.macd import decide_macd


def _df(closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_macd_buys_when_hist_turns_positive():
    # Plano en 10, baja sostenida 9-5 (hist <0 en [-2]), luego spike a 50: hist cruza a >0.
    closes = [10, 10, 10, 10, 10, 10, 10, 10, 9, 8, 7, 6, 5, 50]
    sig = decide_macd(_df(closes), {"fast": 3, "slow": 6, "signal": 2})
    assert sig.action is Action.BUY


def test_macd_sells_when_hist_turns_negative():
    # Plano en 10, sube sostenida 11-15 (hist >0 en [-2]), luego desplome a 1: hist cruza a <0.
    closes = [10, 10, 10, 10, 10, 10, 10, 10, 11, 12, 13, 14, 15, 1]
    sig = decide_macd(_df(closes), {"fast": 3, "slow": 6, "signal": 2})
    assert sig.action is Action.SELL
