from bot.config import Config, StrategyParams, load_config


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
