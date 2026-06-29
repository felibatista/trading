import pandas as pd

from bot.indicators import ema, rsi


def test_ema_of_constant_is_constant():
    s = pd.Series([5.0, 5.0, 5.0, 5.0])
    assert ema(s, 2).iloc[-1] == 5.0


def test_ema_known_value():
    # span=2 -> alpha=2/3; [1,2] con adjust=False -> 5/3
    s = pd.Series([1.0, 2.0])
    assert abs(ema(s, 2).iloc[-1] - (5 / 3)) < 1e-9


def test_rsi_all_gains_is_100():
    s = pd.Series([float(x) for x in range(1, 21)])
    assert rsi(s, 14).iloc[-1] == 100.0


def test_rsi_all_losses_is_0():
    s = pd.Series([float(x) for x in range(20, 0, -1)])
    assert rsi(s, 14).iloc[-1] == 0.0
