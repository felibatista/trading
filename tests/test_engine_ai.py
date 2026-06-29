from bot.ai.advisor import NoopAdvisor
from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, AIVerdict, Signal
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


class StubAdvisor:
    def __init__(self, enabled=True, confirm=True, confidence=0.5, rationale="r", ai_used=True):
        self.enabled = enabled
        self._verdict = AIVerdict(confirm, confidence, rationale, ai_used)
        self.calls = []

    def review(self, ctx):
        self.calls.append(ctx)
        return self._verdict


def make_engine_ai(feed, broker, store, decider, advisor, ai_affects):
    return Engine(
        feed=feed, broker=broker, store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        timeframe="1h", limit=200, clock=CLOCK, log=lambda m: None,
        decider=decider, advisor=advisor, ai_affects_execution=ai_affects,
    )


def _feed():
    return FakeFeed(make_df([float(x) for x in range(1, 61)]))  # último cerrado = 59


def test_ai_veto_blocks_buy_on_paper():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    adv = StubAdvisor(confirm=False, confidence=0.3, rationale="señal débil")
    result = make_engine_ai(_feed(), broker, store, const_decider(Action.BUY), adv, True).run_cycle("BTC/USDT")
    assert result.action == "HOLD"               # la compra fue vetada
    assert store.get_positions("default") == {}
    assert broker.cash() == 10000.0              # no gastó caja
    d = store.recent_decisions("default", 1)[0]
    assert d["action"] == "BUY"                  # la señal cruda se conserva
    assert d["ai_action"] == "HOLD"              # opinión de la IA (veto)
    assert d["ai_confidence"] == 0.3
    assert d["ai_rationale"] == "señal débil"


def test_ai_confirm_allows_buy():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    adv = StubAdvisor(confirm=True, confidence=0.8, rationale="ok")
    result = make_engine_ai(_feed(), broker, store, const_decider(Action.BUY), adv, True).run_cycle("BTC/USDT")
    assert result.action == "BUY"
    assert "BTC/USDT" in store.get_positions("default")
    d = store.recent_decisions("default", 1)[0]
    assert d["ai_action"] == "BUY"
    assert d["ai_confidence"] == 0.8


def test_ai_disabled_noop_buys_without_ai_fields():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    result = make_engine_ai(_feed(), broker, store, const_decider(Action.BUY), NoopAdvisor(), True).run_cycle("BTC/USDT")
    assert result.action == "BUY"
    assert "BTC/USDT" in store.get_positions("default")
    d = store.recent_decisions("default", 1)[0]
    assert d["ai_action"] is None
    assert d["ai_confidence"] is None


def test_ai_never_consulted_for_sell():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    make_engine_ai(_feed(), broker, store, const_decider(Action.BUY), NoopAdvisor(), False).run_cycle("BTC/USDT")
    assert "BTC/USDT" in store.get_positions("default")
    adv = StubAdvisor(confirm=False)  # intentaría vetar
    make_engine_ai(_feed(), broker, store, const_decider(Action.SELL), adv, True).run_cycle("BTC/USDT")
    assert store.get_positions("default") == {}   # la venta de estrategia se ejecuta igual
    assert adv.calls == []               # la IA no se consulta para vender


def test_ai_veto_is_informational_only_when_execution_not_affected():
    # En okx_demo/real (ai_affects_execution=False) la IA opina pero NO bloquea.
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    adv = StubAdvisor(confirm=False, confidence=0.2, rationale="riesgoso")
    result = make_engine_ai(_feed(), broker, store, const_decider(Action.BUY), adv, False).run_cycle("BTC/USDT")
    assert result.action == "BUY"
    assert "BTC/USDT" in store.get_positions("default")   # NO bloquea la ejecución
    d = store.recent_decisions("default", 1)[0]
    assert d["ai_action"] == "HOLD"              # pero el veto queda registrado
    assert d["ai_rationale"] == "riesgoso"


def test_ai_does_not_gate_protective_stop_loss_exit():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    feed = FakeFeed(make_df([100.0, 100.0, 100.0]))
    make_engine_ai(feed, broker, store, const_decider(Action.BUY), NoopAdvisor(), False).run_cycle("BTC/USDT")
    assert "BTC/USDT" in store.get_positions("default")
    feed.df = make_df([90.0, 90.0, 80.0])  # último cerrado 90 < stop (100*0.98)
    adv = StubAdvisor(confirm=False)
    result = make_engine_ai(feed, broker, store, const_decider(Action.HOLD), adv, True).run_cycle("BTC/USDT")
    assert result.action == "SELL"
    assert "stop-loss" in result.detail
    assert store.get_positions("default") == {}
    assert adv.calls == []  # la IA jamás toca un cierre protector
