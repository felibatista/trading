from bot.broker.models import Fill, Side
from bot.store.db import Store


def _seed_equity(s: Store) -> None:
    s.record_equity("2024-01-01T00:00:00+00:00", 10000.0, 10000.0)
    s.record_equity("2024-01-01T01:00:00+00:00", 10100.0, 9000.0)
    s.record_equity("2024-01-01T02:00:00+00:00", 10250.0, 9000.0)


def test_equity_series_oldest_to_newest_limited():
    s = Store(":memory:")
    _seed_equity(s)
    series = s.equity_series(limit=2)
    assert [p["equity"] for p in series] == [10100.0, 10250.0]  # últimos 2, cronológico
    assert series[0]["ts"] == "2024-01-01T01:00:00+00:00"
    assert set(series[0]) == {"ts", "equity", "cash"}


def test_equity_series_all_when_limit_large():
    s = Store(":memory:")
    _seed_equity(s)
    series = s.equity_series(limit=100)
    assert [p["equity"] for p in series] == [10000.0, 10100.0, 10250.0]


def test_recent_fills_newest_first():
    s = Store(":memory:")
    s.record_fill("t1", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05))
    s.record_fill("t2", Fill("BTC/USDT", Side.SELL, 0.5, 110.0, 0.055))
    fills = s.recent_fills(limit=10)
    assert len(fills) == 2
    assert fills[0]["side"] == "SELL"  # más reciente primero
    assert fills[0]["price"] == 110.0
    assert set(fills[0]) == {"ts", "symbol", "side", "quantity", "price", "fee"}


def test_recent_decisions_includes_indicators():
    s = Store(":memory:")
    s.record_decision("t1", "BTC/USDT", "BUY", "cruce alcista", 30.5, 29.0, 41.0)
    d = s.recent_decisions(limit=1)[0]
    assert d["action"] == "BUY"
    assert d["ema_fast"] == 30.5
    assert d["ema_slow"] == 29.0
    assert d["rsi"] == 41.0
