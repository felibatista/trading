# tests/test_fleet.py
from __future__ import annotations

import pandas as pd

from bot.config import Config
from bot.fleet import Fleet
from bot.store.db import Store


def _ramp_feed():
    # Sube fuerte: gatilla el cruce de EMA del scalper (ema_rsi).
    class F:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            closes = [10.0] * 6 + [11, 12, 13, 14, 15, 16, 17]
            n = len(closes)
            return pd.DataFrame({
                "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
                "open": closes, "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
            })
    return F()


def _seed_one(store):
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 1,
                         10000.0, False, True, {"fast": 2, "slow": 4, "rsi_overbought": 90})


def test_run_once_records_decision_per_account():
    store = Store(":memory:")
    _seed_one(store)
    fleet = Fleet(store, Config(), feed_factory=lambda: _ramp_feed())
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 1
    store.close()


def test_disabled_account_is_skipped():
    store = Store(":memory:")
    store.upsert_account("off", "Off", "ema_rsi", "BTC/USDT", "1m", 1,
                         10000.0, False, False, {"fast": 2, "slow": 4})
    fleet = Fleet(store, Config(), feed_factory=lambda: _ramp_feed())
    fleet.run_once()
    assert store.recent_decisions("off") == []
    store.close()


def test_start_then_stop_is_clean():
    store = Store(":memory:")
    _seed_one(store)
    fleet = Fleet(store, Config(), feed_factory=lambda: _ramp_feed())
    fleet.start()
    fleet.stop(timeout=2.0)
    assert all(not t.is_alive() for t in fleet._threads)
    store.close()
