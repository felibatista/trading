from bot.ai.advisor import AnthropicAdvisor, NoopAdvisor
from bot.cli import ai_affects_execution, build_advisor
from bot.config import AIParams, BrokerParams, Config


def test_build_advisor_noop_when_disabled():
    cfg = Config(ai=AIParams(enabled=False))
    assert isinstance(build_advisor(cfg), NoopAdvisor)


def test_build_advisor_anthropic_when_enabled():
    cfg = Config(ai=AIParams(enabled=True, model="claude-haiku-4-5", timeout_seconds=12, max_retries=2))
    adv = build_advisor(cfg)
    assert isinstance(adv, AnthropicAdvisor)  # no instancia el cliente: no necesita API key acá
    assert adv.enabled is True
    assert adv.model == "claude-haiku-4-5"
    assert adv.timeout_seconds == 12
    assert adv.max_retries == 2


def test_ai_affects_execution_only_on_paper_when_enabled():
    assert ai_affects_execution(Config(ai=AIParams(enabled=True), broker=BrokerParams(kind="paper"))) is True
    assert ai_affects_execution(Config(ai=AIParams(enabled=True), broker=BrokerParams(kind="okx_demo"))) is False
    assert ai_affects_execution(Config(ai=AIParams(enabled=False), broker=BrokerParams(kind="paper"))) is False
