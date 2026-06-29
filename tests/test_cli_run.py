from bot.cli import build_broker
from bot.config import BrokerParams, Config
from bot.broker.paper import LocalPaperBroker


def test_build_broker_paper_by_default():
    broker = build_broker(Config())
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 10000.0


def test_build_broker_paper_uses_config_cash():
    cfg = Config(broker=BrokerParams(kind="paper", paper_cash=2500.0))
    broker = build_broker(cfg)
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 2500.0
