from bot.config import BrokerParams, Config, RiskParams, StrategyParams, load_config


def test_load_config_reads_values(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "exchange: kraken\n"
        "timeframe: '4h'\n"
        "symbols:\n"
        "  - ETH/USDT\n"
        "strategy:\n"
        "  fast: 9\n"
        "  slow: 21\n",
        encoding="utf-8",
    )
    c = load_config(p)
    assert c.exchange == "kraken"
    assert c.timeframe == "4h"
    assert c.symbols == ["ETH/USDT"]
    assert c.strategy.fast == 9
    assert c.strategy.slow == 21
    assert c.strategy.rsi_period == 14  # default conservado


def test_load_config_uses_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("{}", encoding="utf-8")
    c = load_config(p)
    assert c == Config()
    assert c.strategy == StrategyParams()


def test_load_config_reads_broker_and_risk(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "db_path: data.sqlite\n"
        "limit: 300\n"
        "broker:\n"
        "  kind: okx_demo\n"
        "  paper_cash: 5000\n"
        "risk:\n"
        "  risk_per_trade: 0.02\n"
        "  max_positions: 5\n",
        encoding="utf-8",
    )
    c = load_config(p)
    assert c.db_path == "data.sqlite"
    assert c.limit == 300
    assert c.broker.kind == "okx_demo"
    assert c.broker.paper_cash == 5000
    assert c.broker.fee_rate == 0.001  # default conservado
    assert c.risk.risk_per_trade == 0.02
    assert c.risk.max_positions == 5
    assert c.risk.stop_loss_pct == 0.02  # default conservado


def test_broker_and_risk_defaults_on_empty(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("{}", encoding="utf-8")
    c = load_config(p)
    assert c.broker == BrokerParams()
    assert c.risk == RiskParams()
    assert c.db_path == "americo.sqlite"
    assert c.loop_interval_seconds == 3600
