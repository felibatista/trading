from bot.broker.models import Fill, Position, Side


def test_fill_fields():
    f = Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05)
    assert f.side is Side.BUY
    assert f.quantity == 0.5
    assert f.price == 100.0
    assert f.fee == 0.05


def test_position_fields():
    p = Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0)
    assert p.stop_loss == 98.0
    assert p.take_profit == 104.0


def test_side_values():
    assert {s.value for s in Side} == {"BUY", "SELL"}
