import json

from bot.ai.advisor import AnthropicAdvisor, NoopAdvisor, OpenAIAdvisor
from bot.models import Action, AIContext, AIVerdict


def ctx() -> AIContext:
    return AIContext(
        symbol="BTC/USDT",
        action=Action.BUY,
        reason="cruce alcista",
        indicators={"ema_fast": 30.5, "ema_slow": 29.0, "rsi": 41.0},
        price=100.0,
        has_position=False,
        risk={"risk_per_trade": 0.01, "stop_loss_pct": 0.02, "take_profit_pct": 0.04},
    )


class _FakeMessages:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kwargs):
        self.parent.calls.append(kwargs)
        if self.parent.raise_exc is not None:
            raise self.parent.raise_exc
        block = type("Block", (), {"type": "tool_use", "name": "emit_verdict",
                                   "input": self.parent.tool_input})()
        return type("Resp", (), {"content": [block]})()


class FakeClient:
    def __init__(self, tool_input=None, raise_exc=None):
        self.tool_input = tool_input
        self.raise_exc = raise_exc
        self.calls = []
        self.messages = _FakeMessages(self)

    def with_options(self, **kwargs):
        return self


def test_noop_advisor_is_passthrough():
    adv = NoopAdvisor()
    assert adv.enabled is False
    v = adv.review(ctx())
    assert isinstance(v, AIVerdict)
    assert v.confirm is True
    assert v.ai_used is False


def test_anthropic_advisor_parses_verdict():
    client = FakeClient(tool_input={"confirm": False, "confidence": 0.3, "rationale": "débil"})
    adv = AnthropicAdvisor(model="claude-haiku-4-5", client=client, log=lambda m: None)
    assert adv.enabled is True
    v = adv.review(ctx())
    assert v.confirm is False
    assert v.confidence == 0.3
    assert v.rationale == "débil"
    assert v.ai_used is True


def test_anthropic_advisor_uses_configured_model():
    client = FakeClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    adv = AnthropicAdvisor(model="claude-sonnet-4-6", client=client, log=lambda m: None)
    adv.review(ctx())
    assert client.calls[0]["model"] == "claude-sonnet-4-6"


def test_anthropic_advisor_falls_back_to_rules_on_error():
    client = FakeClient(raise_exc=RuntimeError("boom"))
    adv = AnthropicAdvisor(model="claude-haiku-4-5", client=client, log=lambda m: None)
    v = adv.review(ctx())
    assert v.confirm is True      # fail-open: se comporta como solo-reglas
    assert v.ai_used is False     # pero queda registrado que la IA no opinó


def test_prompt_carries_no_secrets_or_position_object():
    client = FakeClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    adv = AnthropicAdvisor(model="claude-haiku-4-5", client=client, log=lambda m: None)
    adv.review(ctx())
    sent = client.calls[0]
    payload = str(sent.get("messages", "")) + str(sent.get("system", ""))
    low = payload.lower()
    assert "api_key" not in low and "secret" not in low and "password" not in low
    assert "Position(" not in payload  # nunca se serializa el objeto Position


# ---- OpenAIAdvisor (espejo del de Anthropic, sobre function calling) ----

class _FakeCompletions:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kwargs):
        self.parent.calls.append(kwargs)
        if self.parent.raise_exc is not None:
            raise self.parent.raise_exc
        fn = type("Fn", (), {"name": "emit_verdict",
                             "arguments": json.dumps(self.parent.tool_input)})()
        call = type("Call", (), {"function": fn})()
        msg = type("Msg", (), {"tool_calls": [call]})()
        choice = type("Choice", (), {"message": msg})()
        return type("Resp", (), {"choices": [choice]})()


class FakeOpenAIClient:
    def __init__(self, tool_input=None, raise_exc=None):
        self.tool_input = tool_input
        self.raise_exc = raise_exc
        self.calls = []
        self.chat = type("Chat", (), {"completions": _FakeCompletions(self)})()

    def with_options(self, **kwargs):
        return self


def test_openai_advisor_parses_verdict():
    client = FakeOpenAIClient(tool_input={"confirm": False, "confidence": 0.3, "rationale": "débil"})
    adv = OpenAIAdvisor(model="gpt-4o-mini", client=client, log=lambda m: None)
    assert adv.enabled is True
    v = adv.review(ctx())
    assert v.confirm is False
    assert v.confidence == 0.3
    assert v.rationale == "débil"
    assert v.ai_used is True


def test_openai_advisor_uses_configured_model():
    client = FakeOpenAIClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    adv = OpenAIAdvisor(model="gpt-4o", client=client, log=lambda m: None)
    adv.review(ctx())
    assert client.calls[0]["model"] == "gpt-4o"


def test_openai_advisor_uses_max_completion_tokens():
    # La API nueva de OpenAI deprecó max_tokens en chat completions y los modelos
    # o-series lo rechazan; debe mandarse max_completion_tokens.
    client = FakeOpenAIClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    adv = OpenAIAdvisor(model="gpt-4o-mini", client=client, log=lambda m: None)
    adv.review(ctx())
    sent = client.calls[0]
    assert "max_completion_tokens" in sent and "max_tokens" not in sent


def test_advisors_pin_temperature_zero():
    # Determinismo/reproducibilidad: ambos proveedores fijan temperature=0.
    oc = FakeOpenAIClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    OpenAIAdvisor(model="gpt-4o-mini", client=oc, log=lambda m: None).review(ctx())
    assert oc.calls[0]["temperature"] == 0

    ac = FakeClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    AnthropicAdvisor(model="claude-haiku-4-5", client=ac, log=lambda m: None).review(ctx())
    assert ac.calls[0]["temperature"] == 0


def test_openai_advisor_falls_back_to_rules_on_error():
    client = FakeOpenAIClient(raise_exc=RuntimeError("boom"))
    adv = OpenAIAdvisor(model="gpt-4o-mini", client=client, log=lambda m: None)
    v = adv.review(ctx())
    assert v.confirm is True      # fail-open: se comporta como solo-reglas
    assert v.ai_used is False


def test_openai_prompt_carries_no_secrets_or_position_object():
    client = FakeOpenAIClient(tool_input={"confirm": True, "confidence": 0.9, "rationale": "ok"})
    adv = OpenAIAdvisor(model="gpt-4o-mini", client=client, log=lambda m: None)
    adv.review(ctx())
    payload = str(client.calls[0].get("messages", ""))
    low = payload.lower()
    assert "api_key" not in low and "secret" not in low and "password" not in low
    assert "Position(" not in payload
