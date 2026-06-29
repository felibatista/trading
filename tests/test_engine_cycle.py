from bot.broker.models import Position
from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store
from tests.conftest import make_df

CLOCK = lambda: "2024-01-01T00:00:00+00:00"


class FakeFeed:
    def __init__(self, df):
        self.df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self.df


def const_decider(action, rsi=50.0):
    def _decider(df, params):
        return Signal(action, "test", {"ema_fast": 1.0, "ema_slow": 1.0, "rsi": rsi})
    return _decider


def make_engine(feed, broker, store, decider):
    return Engine(
        feed=feed, broker=broker, store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        timeframe="1h", limit=200, clock=CLOCK, log=lambda m: None,
        decider=decider,
    )


def test_buy_opens_position_and_spends_cash():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))  # último cerrado = 59
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    engine = make_engine(feed, broker, store, const_decider(Action.BUY))
    result = engine.run_cycle("BTC/USDT")
    assert result.action == "BUY"
    assert "BTC/USDT" in store.get_positions("default")
    assert broker.cash() < 10000.0
    assert store.latest_equity("default") is not None


def test_sell_closes_existing_position():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    make_engine(feed, broker, store, const_decider(Action.BUY)).run_cycle("BTC/USDT")
    cash_after_buy = broker.cash()
    make_engine(feed, broker, store, const_decider(Action.SELL)).run_cycle("BTC/USDT")
    assert store.get_positions("default") == {}
    assert broker.cash() > cash_after_buy


def test_stop_loss_exit_when_price_below_stop():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    feed = FakeFeed(make_df([100.0, 100.0, 100.0]))   # último cerrado = 100
    make_engine(feed, broker, store, const_decider(Action.BUY)).run_cycle("BTC/USDT")
    assert "BTC/USDT" in store.get_positions("default")
    feed.df = make_df([90.0, 90.0, 80.0])             # último cerrado = 90
    result = make_engine(feed, broker, store, const_decider(Action.HOLD)).run_cycle("BTC/USDT")
    assert result.action == "SELL"
    assert "stop-loss" in result.detail
    assert store.get_positions("default") == {}


def test_hold_without_position_does_nothing_but_snapshots():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    result = make_engine(feed, broker, store, const_decider(Action.HOLD)).run_cycle("BTC/USDT")
    assert result.action == "HOLD"
    assert store.get_positions("default") == {}
    assert broker.cash() == 10000.0
    assert store.latest_equity("default") is not None
