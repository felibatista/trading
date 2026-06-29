from __future__ import annotations

from bot.accounts import DEFAULT_ACCOUNTS, seed_default_accounts
from bot.store.db import Store


def test_seeds_five_accounts_once():
    s = Store(":memory:")
    seed_default_accounts(s)
    accs = s.list_accounts()
    assert len(accs) == 5
    assert {a["strategy"] for a in accs} == {
        "ema_rsi", "macd", "bollinger", "breakout", "price_action"
    }
    # idempotente: segunda llamada no duplica
    seed_default_accounts(s)
    assert len(s.list_accounts()) == 5
    s.close()


def test_default_accounts_have_required_fields():
    for a in DEFAULT_ACCOUNTS:
        assert {"id", "name", "strategy", "symbol", "timeframe",
                "interval_seconds", "starting_cash", "ai_enabled",
                "enabled", "params"} <= set(a)
        assert isinstance(a["params"], dict)
