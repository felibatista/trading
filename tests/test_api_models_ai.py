from api.models import DecisionOut


def test_decision_out_ai_fields_optional_default_none():
    d = DecisionOut(
        ts="t", symbol="BTC/USDT", action="BUY", reason="x",
        ema_fast=1.0, ema_slow=2.0, rsi=3.0,
    )
    assert d.ai_action is None
    assert d.ai_confidence is None
    assert d.ai_rationale is None


def test_decision_out_accepts_ai_fields():
    d = DecisionOut(
        ts="t", symbol="BTC/USDT", action="BUY", reason="x",
        ema_fast=1.0, ema_slow=2.0, rsi=3.0,
        ai_action="HOLD", ai_confidence=0.4, ai_rationale="débil",
    )
    assert d.ai_action == "HOLD"
    assert d.ai_confidence == 0.4
    assert d.ai_rationale == "débil"
