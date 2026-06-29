# tests/test_store_fills_positions.py
from __future__ import annotations

from bot.broker.models import Fill, Position, Side
from bot.store.db import Store


def test_fills_roundtrip_by_account():
    s = Store(":memory:")
    s.record_fill("a", "2026-01-01T00:00:00+00:00", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.1))
    rows = s.recent_fills("a")
    assert rows[0]["side"] == "BUY" and rows[0]["quantity"] == 0.5
    assert s.recent_fills("b") == []
    s.close()


def test_positions_upsert_and_remove():
    s = Store(":memory:")
    s.upsert_position("a", Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0), "2026-01-01T00:00:00+00:00")
    s.upsert_position("a", Position("BTC/USDT", 0.7, 101.0, 99.0, 105.0), "2026-01-01T00:01:00+00:00")
    pos = s.get_positions("a")
    assert set(pos) == {"BTC/USDT"} and pos["BTC/USDT"].quantity == 0.7  # update, no duplicado
    assert s.get_positions("b") == {}
    s.remove_position("a", "BTC/USDT")
    assert s.get_positions("a") == {}
    s.close()
