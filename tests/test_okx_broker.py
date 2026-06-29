from bot.broker.models import Side
from bot.broker.okx_demo import OkxDemoBroker


class FakeExchange:
    def __init__(self):
        self.calls = []

    def create_market_buy_order(self, symbol, quantity):
        self.calls.append(("buy", symbol, quantity))
        return {"average": 100.0, "filled": quantity, "fee": {"cost": 0.1}}

    def create_market_sell_order(self, symbol, quantity):
        self.calls.append(("sell", symbol, quantity))
        return {"average": 110.0, "filled": quantity, "fee": {"cost": 0.11}}

    def fetch_balance(self):
        return {"free": {"USDT": 5000.0}}


def test_buy_calls_exchange_and_parses_fill():
    ex = FakeExchange()
    b = OkxDemoBroker("k", "s", "p", exchange=ex)
    fill = b.buy("BTC/USDT", 0.5, ref_price=0.0)
    assert ex.calls == [("buy", "BTC/USDT", 0.5)]
    assert fill.side is Side.BUY
    assert fill.price == 100.0
    assert fill.quantity == 0.5
    assert fill.fee == 0.1


def test_sell_calls_exchange_and_parses_fill():
    ex = FakeExchange()
    b = OkxDemoBroker("k", "s", "p", exchange=ex)
    fill = b.sell("BTC/USDT", 0.5, ref_price=0.0)
    assert ex.calls == [("sell", "BTC/USDT", 0.5)]
    assert fill.side is Side.SELL
    assert fill.price == 110.0
    assert fill.fee == 0.11


def test_cash_reads_free_quote_balance():
    b = OkxDemoBroker("k", "s", "p", exchange=FakeExchange())
    assert b.cash() == 5000.0
