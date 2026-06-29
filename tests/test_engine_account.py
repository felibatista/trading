from __future__ import annotations

import pandas as pd

from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store


class _Feed:
    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        # 3 velas: la última se descarta (drop_forming_candle), decide sobre la previa.
        return pd.DataFrame({
            "timestamp": pd.to_datetime([1, 2, 3], unit="ms", utc=True),
            "open": [100, 100, 100], "high": [100, 100, 100],
            "low": [100, 100, 100], "close": [100, 100, 100], "volume": [1, 1, 1],
        })


class _Broker:
    def cash(self): return 10000.0


def _hold(df, params):
    return Signal(Action.HOLD, "sin señal", {"ema_fast": 1.0, "ema_slow": 2.0, "rsi": 50.0})


def test_engine_writes_under_its_account():
    store = Store(":memory:")
    eng = Engine(_Feed(), _Broker(), store, StrategyParams(), RiskParams(),
                 timeframe="1m", limit=3, decider=_hold, account="acc1")
    eng.run_cycle("BTC/USDT")
    assert len(store.recent_decisions("acc1")) == 1
    assert store.recent_decisions("default") == []
    store.close()
