from __future__ import annotations

import pandas as pd

from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.store.db import Store


class _ShortFeed:
    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        # 2 filas -> tras drop_forming_candle queda 1 -> insuficiente.
        return pd.DataFrame({
            "timestamp": pd.to_datetime([1, 2], unit="ms", utc=True),
            "open": [100, 100], "high": [100, 100],
            "low": [100, 100], "close": [100, 100], "volume": [1, 1],
        })


class _Broker:
    def cash(self): return 10000.0


def test_run_cycle_holds_on_insufficient_data():
    store = Store(":memory:")
    eng = Engine(_ShortFeed(), _Broker(), store, StrategyParams(), RiskParams(),
                 timeframe="1m", limit=2, account="acc")
    res = eng.run_cycle("BTC/USDT")
    assert res.action == "HOLD"
    assert store.recent_fills("acc") == []  # no operó
    store.close()
