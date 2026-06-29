from bot.config import AIParams, Config, load_config


def test_ai_defaults_on_config_dataclass():
    cfg = Config()
    assert isinstance(cfg.ai, AIParams)
    assert cfg.ai.enabled is False  # seguro por defecto en el código
    assert cfg.ai.model == "claude-haiku-4-5"


def test_ai_defaults_when_section_absent(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("exchange: okx\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg.ai.enabled is False
    assert cfg.ai.model == "claude-haiku-4-5"
    assert cfg.ai.timeout_seconds == 20.0
    assert cfg.ai.max_retries == 1


def test_ai_parsed_from_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "ai:\n"
        "  enabled: true\n"
        "  model: claude-sonnet-4-6\n"
        "  timeout_seconds: 12\n"
        "  max_retries: 2\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.ai.enabled is True
    assert cfg.ai.model == "claude-sonnet-4-6"
    assert cfg.ai.timeout_seconds == 12.0
    assert cfg.ai.max_retries == 2
