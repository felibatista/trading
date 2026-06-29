# tests/test_fleet_hotreload.py
from __future__ import annotations

import pandas as pd

from bot.config import Config
from bot.fleet import Fleet
from bot.store.db import Store


def _feed():
    class F:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            closes = [100.0 + (i % 5) for i in range(40)]
            n = len(closes)
            return pd.DataFrame({
                "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
                "open": closes, "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
            })
    return F()


def _seed(store, enabled=True):
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 1,
                         10000.0, False, enabled, {"fast": 2, "slow": 4})


def test_config_sig_changes_with_params():
    store = Store(":memory:")
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    a1 = {"strategy": "ema_rsi", "params": {"fast": 2}, "symbol": "BTC/USDT",
          "timeframe": "1m", "ai_enabled": False}
    a2 = {**a1, "params": {"fast": 3}}
    assert fleet._config_sig(a1) != fleet._config_sig(a2)
    store.close()


def test_config_sig_changes_with_provider_and_model():
    store = Store(":memory:")
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    base = {"strategy": "ema_rsi", "params": {"fast": 2}, "symbol": "BTC/USDT",
            "timeframe": "1m", "ai_enabled": True,
            "ai_provider": "anthropic", "ai_model": "claude-haiku-4-5"}
    assert fleet._config_sig(base) != fleet._config_sig({**base, "ai_provider": "openai"})
    assert fleet._config_sig(base) != fleet._config_sig({**base, "ai_model": "gpt-4o-mini"})
    store.close()


def test_run_once_respects_live_enabled_flag():
    store = Store(":memory:")
    _seed(store, enabled=True)
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 1
    # pausar -> no opera
    store.set_account_enabled("scalper", False)
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 1
    # reanudar -> vuelve a operar
    store.set_account_enabled("scalper", True)
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 2
    store.close()
