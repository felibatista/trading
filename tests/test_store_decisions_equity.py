# tests/test_store_decisions_equity.py
from __future__ import annotations

from bot.store.db import Store


def test_decisions_isolated_by_account():
    s = Store(":memory:")
    s.record_decision("a", "2026-01-01T00:00:00+00:00", "BTC/USDT", "BUY", "r", 1.0, 2.0, 30.0)
    s.record_decision("b", "2026-01-01T00:00:01+00:00", "ETH/USDT", "SELL", "r2", 3.0, 4.0, 70.0)
    a = s.recent_decisions("a")
    assert len(a) == 1 and a[0]["symbol"] == "BTC/USDT" and a[0]["action"] == "BUY"
    assert a[0]["ema_fast"] == 1.0 and a[0]["rsi"] == 30.0
    assert len(s.recent_decisions("b")) == 1
    s.close()


def test_equity_latest_and_series_by_account():
    s = Store(":memory:")
    s.record_equity("a", "2026-01-01T00:00:00+00:00", 10000.0, 10000.0)
    s.record_equity("a", "2026-01-01T00:01:00+00:00", 10100.0, 9000.0)
    assert s.latest_equity("a") == (10100.0, 9000.0)
    assert s.latest_equity("b") is None
    series = s.equity_series("a")
    assert [p["equity"] for p in series] == [10000.0, 10100.0]  # cronológico
    s.close()
