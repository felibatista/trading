from __future__ import annotations

import pandas as pd
import pytest

from bot.models import Action
from bot.strategy.registry import available, get_strategy


def _crossover_df():
    # Bajada sostenida (EMA rápida por debajo de la lenta) + rebote fuerte final.
    # Con fast=2, slow=4: la EMA(2) cruza hacia arriba en la última vela.
    # Las pérdidas previas dejan RSI(3) < 90 (≈87), evitando el veto de sobrecompra.
    closes = [10, 10, 10, 10, 10, 10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 15]
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_registry_has_ema_rsi():
    assert "ema_rsi" in available()


def test_unknown_strategy_raises():
    with pytest.raises(KeyError):
        get_strategy("noexiste")


def test_ema_rsi_buys_on_crossover():
    fn = get_strategy("ema_rsi")
    sig = fn(_crossover_df(), {"fast": 2, "slow": 4, "rsi_period": 3, "rsi_overbought": 90})
    assert sig.action is Action.BUY
