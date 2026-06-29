from bot.models import Action, Signal


def test_signal_has_defaults():
    s = Signal(Action.HOLD, "sin señal")
    assert s.action is Action.HOLD
    assert s.reason == "sin señal"
    assert s.indicators == {}


def test_action_values():
    assert Action.BUY.value == "BUY"
    assert {a.value for a in Action} == {"BUY", "SELL", "HOLD"}
