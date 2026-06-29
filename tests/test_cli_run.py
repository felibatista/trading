import pytest

from bot.broker.models import Position
from bot.broker.paper import LocalPaperBroker
from bot.cli import build_broker
from bot.config import BrokerParams, Config
from bot.store.db import Store


def test_build_broker_paper_by_default():
    broker = build_broker(Config())
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 10000.0


def test_build_broker_paper_uses_config_cash():
    cfg = Config(broker=BrokerParams(kind="paper", paper_cash=2500.0))
    broker = build_broker(cfg)
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 2500.0


def test_build_broker_hydrates_paper_from_store():
    store = Store(":memory:")
    store.upsert_position(Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0), "t1")
    store.record_equity("t1", 10050.0, 9000.0)
    broker = build_broker(Config(), store)
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 9000.0                 # restored from last equity snapshot cash
    assert broker.holdings("BTC/USDT") == 0.5       # restored from store positions


def test_build_broker_unknown_kind_raises():
    with pytest.raises(ValueError):
        build_broker(Config(broker=BrokerParams(kind="nope")))
