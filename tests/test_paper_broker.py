import pytest

from bot.broker.models import Side
from bot.broker.paper import LocalPaperBroker


def test_buy_deducts_cash_with_fee_and_slippage():
    b = LocalPaperBroker(cash=10000.0, fee_rate=0.001, slippage=0.0005)
    fill = b.buy("BTC/USDT", 0.1, ref_price=100.0)
    assert fill.side is Side.BUY
    assert abs(fill.price - 100.05) < 1e-9          # 100 * (1 + 0.0005)
    assert abs(fill.fee - 0.010005) < 1e-9          # 0.1*100.05*0.001
    assert abs(b.cash() - 9989.984995) < 1e-6       # 10000 - (10.005 + 0.010005)
    assert abs(b.holdings("BTC/USDT") - 0.1) < 1e-12


def test_sell_adds_cash_and_reduces_holdings():
    b = LocalPaperBroker(cash=10000.0, fee_rate=0.001, slippage=0.0005)
    b.buy("BTC/USDT", 0.1, ref_price=100.0)
    fill = b.sell("BTC/USDT", 0.1, ref_price=110.0)
    assert fill.side is Side.SELL
    assert abs(fill.price - 109.945) < 1e-9          # 110 * (1 - 0.0005)
    assert abs(b.cash() - 10000.9685005) < 1e-6
    assert abs(b.holdings("BTC/USDT")) < 1e-12


def test_buy_without_cash_raises():
    b = LocalPaperBroker(cash=5.0)
    with pytest.raises(ValueError):
        b.buy("BTC/USDT", 1.0, ref_price=100.0)


def test_sell_without_position_raises():
    b = LocalPaperBroker(cash=10000.0)
    with pytest.raises(ValueError):
        b.sell("BTC/USDT", 1.0, ref_price=100.0)


def test_initial_holdings_are_restored():
    b = LocalPaperBroker(cash=9000.0, holdings={"BTC/USDT": 0.5})
    assert b.holdings("BTC/USDT") == 0.5
    b.sell("BTC/USDT", 0.5, ref_price=100.0)
    assert abs(b.holdings("BTC/USDT")) < 1e-12
