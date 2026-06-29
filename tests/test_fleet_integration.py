from __future__ import annotations

import pandas as pd

from bot.accounts import seed_default_accounts
from bot.config import Config
from bot.fleet import Fleet
from bot.store.db import Store


def _feed():
    class F:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            closes = [100.0 + (i % 7) for i in range(60)]
            n = len(closes)
            return pd.DataFrame({
                "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
                "open": closes, "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
            })
    return F()


def test_fleet_runs_all_five_accounts_once():
    store = Store(":memory:")
    seed_default_accounts(store)
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    fleet.run_once()
    # cada cuenta registró al menos una decisión bajo su id
    for acc_id in ("scalper", "momentum", "reversion", "ruptura", "price"):
        assert len(store.recent_decisions(acc_id)) == 1
    store.close()
