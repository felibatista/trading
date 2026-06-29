# tests/test_store_accounts.py
from __future__ import annotations

from bot.store.db import Store


def _seed(s):
    s.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                     10000.0, True, True, {"fast": 2, "slow": 4})


def test_account_crud():
    s = Store(":memory:")
    _seed(s)
    got = s.get_account("scalper")
    assert got["strategy"] == "ema_rsi" and got["params"] == {"fast": 2, "slow": 4}
    assert got["ai_enabled"] is True and got["interval_seconds"] == 12
    s.upsert_account("scalper", "Scalper 2", "ema_rsi", "BTC/USDT", "1m", 15,
                     10000.0, True, True, {"fast": 3, "slow": 8})
    assert s.get_account("scalper")["name"] == "Scalper 2"  # update, no duplica
    assert len(s.list_accounts()) == 1
    s.set_account_enabled("scalper", False)
    assert s.get_account("scalper")["enabled"] is False
    assert s.get_account("noexiste") is None
    s.close()
