from api.models import DecisionOut, EquityPoint, FillOut, PositionOut, StatusResponse


def test_status_response_fields():
    s = StatusResponse(
        exchange="okx", timeframe="1h", broker_kind="paper",
        symbols=["BTC/USDT"], equity=10000.0, cash=9000.0,
    )
    assert s.broker_kind == "paper"
    assert s.symbols == ["BTC/USDT"]


def test_models_serialize():
    assert EquityPoint(ts="t", equity=1.0, cash=2.0).model_dump() == {
        "ts": "t", "equity": 1.0, "cash": 2.0,
    }
    assert PositionOut(
        symbol="BTC/USDT", quantity=1.0, entry_price=2.0, stop_loss=1.0, take_profit=3.0,
    ).symbol == "BTC/USDT"
    assert DecisionOut(
        ts="t", symbol="BTC/USDT", action="BUY", reason="x",
        ema_fast=1.0, ema_slow=2.0, rsi=3.0,
    ).action == "BUY"
    assert FillOut(
        ts="t", symbol="BTC/USDT", side="BUY", quantity=1.0, price=2.0, fee=0.1,
    ).side == "BUY"
