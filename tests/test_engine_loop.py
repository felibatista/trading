from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store
from tests.conftest import make_df


class FakeFeed:
    def __init__(self, df):
        self.df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self.df


def hold_decider(df, params):
    return Signal(Action.HOLD, "test", {"ema_fast": 1.0, "ema_slow": 1.0, "rsi": 50.0})


def test_run_loop_runs_each_symbol_per_cycle_and_sleeps_between():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    store = Store(":memory:")
    sleeps = []
    engine = Engine(
        feed=feed, broker=LocalPaperBroker(cash=10000.0), store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        clock=lambda: "t", log=lambda m: None, decider=hold_decider,
    )
    cycles = engine.run_loop(
        ["BTC/USDT", "ETH/USDT"], interval_seconds=10, max_cycles=2,
        sleep=lambda s: sleeps.append(s),
    )
    assert cycles == 2
    assert len(store.recent_decisions("default", limit=100)) == 4   # 2 símbolos * 2 ciclos
    assert sleeps == [10]                                 # duerme una vez (entre ciclos)


def test_run_loop_isolates_per_symbol_errors():
    store = Store(":memory:")

    class BoomFeed:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            if symbol == "BOOM/USDT":
                raise RuntimeError("feed caído")
            return make_df([float(x) for x in range(1, 61)])

    logs = []
    engine = Engine(
        feed=BoomFeed(), broker=LocalPaperBroker(cash=10000.0), store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        clock=lambda: "t", log=lambda m: logs.append(m), decider=hold_decider,
    )
    cycles = engine.run_loop(
        ["BOOM/USDT", "BTC/USDT"], interval_seconds=1, max_cycles=1, sleep=lambda s: None
    )
    assert cycles == 1
    actions = [d["symbol"] for d in store.recent_decisions("default", limit=100)]
    assert "BTC/USDT" in actions
    assert any("ERROR" in m for m in logs)
