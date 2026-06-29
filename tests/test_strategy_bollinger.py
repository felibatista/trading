from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.bollinger import decide_bollinger


def _df(closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_bollinger_buys_on_reentry_from_below():
    # Estable en 100, un pinchazo abajo (95) y reentra (100): rebote de banda inferior.
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 95, 100]
    sig = decide_bollinger(_df(closes), {"period": 5, "num_std": 2.0})
    assert sig.action is Action.BUY


def test_bollinger_sells_on_reentry_from_above():
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 105, 100]
    sig = decide_bollinger(_df(closes), {"period": 5, "num_std": 2.0})
    assert sig.action is Action.SELL
