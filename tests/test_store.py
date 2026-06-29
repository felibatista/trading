from bot.broker.models import Fill, Position, Side
from bot.store.db import Store


def test_decisions_round_trip():
    s = Store(":memory:")
    s.record_decision("default", "t1", "BTC/USDT", "HOLD", "sin señal", 1.0, 2.0, 50.0)
    s.record_decision("default", "t2", "BTC/USDT", "BUY", "cruce", 3.0, 2.0, 40.0)
    recent = s.recent_decisions("default", limit=10)
    assert len(recent) == 2
    assert recent[0]["action"] == "BUY"  # más reciente primero
    assert recent[0]["reason"] == "cruce"


def test_positions_upsert_get_remove():
    s = Store(":memory:")
    s.upsert_position("default", Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0), "t1")
    pos = s.get_positions("default")
    assert set(pos) == {"BTC/USDT"}
    assert pos["BTC/USDT"].entry_price == 100.0
    s.upsert_position("default", Position("BTC/USDT", 0.7, 101.0, 99.0, 105.0), "t2")
    assert s.get_positions("default")["BTC/USDT"].quantity == 0.7  # actualiza, no duplica
    s.remove_position("default", "BTC/USDT")
    assert s.get_positions("default") == {}


def test_fill_and_equity():
    s = Store(":memory:")
    s.record_fill("default", "t1", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05))
    assert s.latest_equity("default") is None
    s.record_equity("default", "t1", 10000.0, 9000.0)
    s.record_equity("default", "t2", 10100.0, 9100.0)
    assert s.latest_equity("default") == (10100.0, 9100.0)  # último
