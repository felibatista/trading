from __future__ import annotations

import pandas as pd

from bot.models import Signal
from bot.strategy.registry import available, get_strategy

EXPECTED = {"ema_rsi", "macd", "bollinger", "breakout", "price_action"}


def _flat_df(n=40):
    closes = [100.0] * n
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_all_five_registered():
    assert EXPECTED <= set(available())


def test_each_strategy_returns_signal_on_flat_market():
    df = _flat_df()
    for name in EXPECTED:
        sig = get_strategy(name)(df, {})
        assert isinstance(sig, Signal)
