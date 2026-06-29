from bot.config import StrategyParams
from bot.models import Action
from bot.strategy.ema_rsi import Features, compute_features, decide, evaluate

P = StrategyParams()


def test_decide_buy_on_bullish_cross():
    f = Features(ema_fast=11, ema_slow=10, ema_fast_prev=9, ema_slow_prev=10, rsi=40)
    assert decide(f, P).action is Action.BUY


def test_decide_sell_on_bearish_cross():
    f = Features(ema_fast=9, ema_slow=10, ema_fast_prev=11, ema_slow_prev=10, rsi=50)
    assert decide(f, P).action is Action.SELL


def test_decide_sell_on_overbought():
    f = Features(ema_fast=10, ema_slow=10, ema_fast_prev=10, ema_slow_prev=10, rsi=75)
    assert decide(f, P).action is Action.SELL


def test_decide_hold_when_neutral():
    f = Features(ema_fast=10.5, ema_slow=10.0, ema_fast_prev=10.4, ema_slow_prev=10.0, rsi=55)
    assert decide(f, P).action is Action.HOLD


def test_compute_features_uptrend(uptrend_df):
    feats = compute_features(uptrend_df, P)
    assert feats.ema_fast > feats.ema_slow
    assert feats.rsi > 50


def test_evaluate_returns_signal(uptrend_df):
    sig = evaluate(uptrend_df, P)
    assert sig.action in (Action.BUY, Action.SELL, Action.HOLD)
    assert set(sig.indicators) == {"ema_fast", "ema_slow", "rsi"}
