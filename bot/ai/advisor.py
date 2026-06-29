from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from bot.models import AIContext, AIVerdict

# La IA es un FILTRO AUXILIAR: solo decide `confirm` (mantener) o vetar la COMPRA.
# Nunca propone un lado ni puede forzar una operación; eso lo garantiza el motor.
SYSTEM_PROMPT = (
    "Sos un filtro de riesgo auxiliar de un bot de trading cripto en SIMULACIÓN (paper). "
    "La estrategia determinística (cruce de EMAs + RSI) ya es la fuente de verdad y "
    "propone una COMPRA. Tu único trabajo es confirmarla o vetarla con una justificación "
    "breve, en base al contexto NUMÉRICO que recibís. Sé conservador: vetá solo si las "
    "señales son débiles o contradictorias (p. ej. RSI alto cerca de sobrecompra, cruce "
    "marginal). No generás alfa por tu cuenta; ante la duda, confirmá. Respondé SIEMPRE "
    "invocando la herramienta emit_verdict (confirm, confidence 0..1, rationale en español)."
)

# JSON-Schema del veredicto, compartido por ambos proveedores para que no se
# desincronicen. Anthropic lo usa como `input_schema`; OpenAI como `function.parameters`.
VERDICT_PARAMS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "confirm": {
            "type": "boolean",
            "description": "true = mantener la COMPRA; false = vetar (no comprar).",
        },
        "confidence": {
            "type": "number",
            "description": "Confianza de 0.0 a 1.0.",
        },
        "rationale": {
            "type": "string",
            "description": "Justificación breve en español.",
        },
    },
    "required": ["confirm", "confidence", "rationale"],
}

_VERDICT_DESC = "Emite el veredicto sobre la compra propuesta por la estrategia."

# Formato Anthropic (tools de la Messages API).
VERDICT_TOOL: dict[str, Any] = {
    "name": "emit_verdict",
    "description": _VERDICT_DESC,
    "input_schema": VERDICT_PARAMS,
}

# Formato OpenAI (function calling de Chat Completions).
OPENAI_VERDICT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "emit_verdict",
        "description": _VERDICT_DESC,
        "parameters": VERDICT_PARAMS,
    },
}

# Modelo por defecto de cada proveedor (coincide con el default __init__ de cada advisor).
# Fuente de verdad para resetear el modelo cuando se cambia de proveedor sin elegir uno.
DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "anthropic": "claude-haiku-4-5",
    "openai": "gpt-4o-mini",
}


class AIAdvisor(Protocol):
    enabled: bool

    def review(self, ctx: AIContext) -> AIVerdict: ...


class NoopAdvisor:
    """Passthrough no-op (IA apagada): siempre confirma, sin red ni dependencias."""

    enabled = False

    def review(self, ctx: AIContext) -> AIVerdict:
        return AIVerdict(confirm=True, confidence=1.0, rationale="ai-off", ai_used=False)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def render_context(ctx: AIContext) -> str:
    ind = ctx.indicators
    risk = ", ".join(f"{k}={v}" for k, v in sorted(ctx.risk.items()))
    return (
        f"Símbolo: {ctx.symbol}\n"
        f"Acción propuesta por la estrategia: {ctx.action.value} (motivo: {ctx.reason})\n"
        f"Indicadores: EMA_fast={ind.get('ema_fast')}, "
        f"EMA_slow={ind.get('ema_slow')}, RSI={ind.get('rsi')}\n"
        f"Precio: {ctx.price}\n"
        f"¿Hay posición abierta?: {'sí' if ctx.has_position else 'no'}\n"
        f"Parámetros de riesgo (conservadores): {risk}\n"
        "¿La compra es razonable con esta configuración? Confirmá o vetá."
    )


def _extract_verdict_input(response: Any) -> dict:
    for block in getattr(response, "content", []):
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "emit_verdict":
            return dict(block.input)
    raise ValueError("la respuesta no contiene un bloque tool_use 'emit_verdict'")


def _extract_openai_verdict_input(response: Any) -> dict:
    # OpenAI devuelve los argumentos de la función como JSON string en
    # choices[0].message.tool_calls[].function.arguments.
    for choice in getattr(response, "choices", []):
        message = getattr(choice, "message", None)
        for call in getattr(message, "tool_calls", None) or []:
            fn = getattr(call, "function", None)
            if getattr(fn, "name", None) == "emit_verdict":
                return dict(json.loads(fn.arguments))
    raise ValueError("la respuesta no contiene un tool_call 'emit_verdict'")


class AnthropicAdvisor:
    """Asesor real sobre la API de Claude. Tolerante a fallos: ante cualquier
    error/timeout cae a 'solo-reglas' (confirm=True, ai_used=False) para que el
    bot se comporte exactamente como el motor determinista."""

    enabled = True

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
        client: Any | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client
        self.log = log

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic  # import perezoso: solo si la IA está prendida

            # La API key se resuelve de ANTHROPIC_API_KEY del entorno; nunca acá.
            self._client = anthropic.Anthropic()
        return self._client

    def review(self, ctx: AIContext) -> AIVerdict:
        try:
            client = self._get_client().with_options(
                timeout=self.timeout_seconds, max_retries=self.max_retries
            )
            response = client.messages.create(
                model=self.model,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                tools=[VERDICT_TOOL],
                tool_choice={"type": "tool", "name": "emit_verdict"},
                messages=[{"role": "user", "content": render_context(ctx)}],
            )
            data = _extract_verdict_input(response)
            return AIVerdict(
                confirm=bool(data["confirm"]),
                confidence=_clamp01(float(data.get("confidence", 0.0))),
                rationale=str(data.get("rationale", ""))[:500],
                ai_used=True,
            )
        except Exception as exc:  # noqa: BLE001 - fail-safe a solo-reglas
            self.log(f"[AI] fallback a solo-reglas: {exc}")
            return AIVerdict(
                confirm=True, confidence=1.0, rationale=f"fallback: {exc}", ai_used=False
            )


class OpenAIAdvisor:
    """Asesor real sobre la API de OpenAI (Chat Completions + function calling).
    Mismo contrato veto-only que AnthropicAdvisor: ante cualquier error/timeout cae a
    'solo-reglas' (confirm=True, ai_used=False) para comportarse como el motor."""

    enabled = True

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
        client: Any | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client = client
        self.log = log

    def _get_client(self) -> Any:
        if self._client is None:
            import openai  # import perezoso: solo si la IA está prendida

            # La API key se resuelve de OPENAI_API_KEY del entorno; nunca acá.
            self._client = openai.OpenAI()
        return self._client

    def review(self, ctx: AIContext) -> AIVerdict:
        try:
            client = self._get_client().with_options(
                timeout=self.timeout_seconds, max_retries=self.max_retries
            )
            response = client.chat.completions.create(
                model=self.model,
                # max_completion_tokens (no el viejo max_tokens) para que también los
                # modelos de razonamiento (o-series) acepten el límite; con holgura para
                # que alcancen a emitir el tool_call forzado.
                max_completion_tokens=1024,
                tools=[OPENAI_VERDICT_TOOL],
                tool_choice={"type": "function", "function": {"name": "emit_verdict"}},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": render_context(ctx)},
                ],
            )
            data = _extract_openai_verdict_input(response)
            return AIVerdict(
                confirm=bool(data["confirm"]),
                confidence=_clamp01(float(data.get("confidence", 0.0))),
                rationale=str(data.get("rationale", ""))[:500],
                ai_used=True,
            )
        except Exception as exc:  # noqa: BLE001 - fail-safe a solo-reglas
            self.log(f"[AI] fallback a solo-reglas: {exc}")
            return AIVerdict(
                confirm=True, confidence=1.0, rationale=f"fallback: {exc}", ai_used=False
            )
