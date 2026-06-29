# Soporte OpenAI: proveedor de IA por cuenta

**Fecha:** 2026-06-29
**Estado:** aprobado (diseño)

## Contexto

La IA del bot es un **filtro veto-only de entradas**: solo confirma o veta una COMPRA
ya propuesta por la estrategia determinística, con fail-safe a "solo-reglas" ante
cualquier error. Hoy existe un único proveedor implícito (Anthropic/Claude) vía
`AnthropicAdvisor`, y el modelo es **global** (`config.ai.model`); por cuenta solo hay
un toggle on/off (`ai_enabled`).

Objetivo: permitir usar **OpenAI** además de Claude, eligiendo **proveedor y modelo por
cuenta** desde el panel. Sin la API key del proveedor elegido, esa cuenta cae a
solo-reglas (igual que hoy), sin romper nada.

## Decisiones tomadas

- **Selección de proveedor:** campo explícito `ai_provider` (`anthropic` | `openai`),
  no auto-detección por nombre de modelo ni por key presente.
- **Alcance:** **por cuenta**. Cada cuenta tiene su `ai_provider` y su `ai_model`.
- **Default OpenAI:** `gpt-4o-mini` (barato, equivalente a Claude Haiku para un veto de
  una sola llamada por entrada).
- **`timeout_seconds` / `max_retries`:** siguen **globales** (`config.ai`); son tuning
  operativo, no se editan por cuenta.
- **Default de modelo al cambiar de proveedor:** lo decide el **panel** (manda el modelo
  ya resuelto en el patch). El backend solo persiste lo que llega; no acopla nombres de
  modelos. El backend valida `ai_provider ∈ {anthropic, openai}` pero **no** valida el
  string de modelo (los nombres cambian; el advisor cae a reglas si es inválido).

## Arquitectura

El flujo de IA no cambia: el `Engine` consulta `advisor.review(ctx)` solo en entradas
(COMPRA) que podrían ejecutarse. Lo que cambia es **qué advisor se construye** por cuenta.

```
Account(ai_provider, ai_model)  ──►  make_advisor(provider, model, timeout, retries)
                                         ├─ "openai"    -> OpenAIAdvisor
                                         └─ "anthropic" -> AnthropicAdvisor
                                      (ai_enabled=false / global off -> None -> NoopAdvisor)
```

### Componentes

1. **`bot/ai/advisor.py` — `OpenAIAdvisor` (nuevo)**
   Espejo de `AnthropicAdvisor`:
   - Cliente perezoso: `import openai` dentro del método, `openai.OpenAI()` (key desde
     `OPENAI_API_KEY`, nunca en código). `with_options(timeout=, max_retries=)`.
   - Function calling con `emit_verdict` (mismo esquema). Llama
     `chat.completions.create(model=..., max_tokens=512, messages=[system, user],
     tools=[OPENAI_VERDICT_TOOL], tool_choice={"type":"function","function":{"name":"emit_verdict"}})`.
   - Parseo: `resp.choices[0].message.tool_calls[0].function.arguments` (JSON string) →
     `json.loads`.
   - Fail-safe idéntico: ante cualquier excepción devuelve
     `AIVerdict(confirm=True, confidence=1.0, ai_used=False)` y loguea el fallback.
   - **Esquema compartido:** se extrae el JSON-Schema del veredicto a una constante
     (`VERDICT_PARAMS`) y desde ahí se arman `VERDICT_TOOL` (Anthropic, `input_schema`) y
     `OPENAI_VERDICT_TOOL` (OpenAI, `function.parameters`), para que no se desincronicen.
   - Reutiliza `SYSTEM_PROMPT`, `render_context`, `_clamp01`. Diferencia con Anthropic:
     `system` viaja como mensaje `role:"system"` (no como parámetro top-level).

2. **`bot/config.py`**
   `AIParams` suma `provider: str = "anthropic"` (default de semilla y del path CLI). Se
   lee en `load_config` (`ai.get("provider", "anthropic")`).

3. **`bot/cli.py` — factory**
   - `make_advisor(provider, model, timeout_seconds, max_retries) -> AIAdvisor`:
     `OpenAIAdvisor` si `provider == "openai"`, si no `AnthropicAdvisor`.
   - `build_advisor(config)` delega en `make_advisor(config.ai.provider, config.ai.model,
     …)` cuando `config.ai.enabled`; si no, `NoopAdvisor`.

4. **`bot/fleet.py`**
   - `_build_engine` construye el advisor con el **provider/model de la cuenta**:
     `make_advisor(account["ai_provider"], account["ai_model"], cfg.ai.timeout_seconds,
     cfg.ai.max_retries)` cuando `ai_on and cfg.ai.enabled`.
   - `_config_sig` incluye `ai_provider` y `ai_model` (hot-reload los toma).

5. **Persistencia**
   - `bot/store/schema.py`: tabla `accounts` suma `ai_provider` (Text) y `ai_model` (Text).
   - `bot/store/db.py`: migración idempotente **cross-dialect** (SQLite y Postgres) que
     hace `ALTER TABLE accounts ADD COLUMN … DEFAULT …` si faltan, backfilleando las
     cuentas ya sembradas (`ai_provider='anthropic'`, `ai_model='claude-haiku-4-5'`).
     `upsert_account` suma `ai_provider`/`ai_model` (con default para no romper llamadas
     existentes). `list_accounts`/`get_account` ya devuelven todas las columnas.
   - `bot/accounts.py`: cada cuenta default setea `ai_provider='anthropic'`,
     `ai_model='claude-haiku-4-5'`.

6. **API**
   - `api/models.py`: `AccountOut` expone `ai_provider`/`ai_model`. `AccountUpdate` los
     acepta; validador `ai_provider ∈ {anthropic, openai}`. `ai_model` libre (no se valida).
   - `api/app.py`: `accounts_list` y `update_account` incluyen los dos campos en la
     respuesta y el PUT los persiste vía `upsert_account`.

7. **Panel**
   - `web/src/lib/types.ts`: `Account` suma `ai_provider: string`, `ai_model: string`.
   - `web/src/components/AccountConfig.tsx`: `<select>` de proveedor
     (Anthropic/OpenAI) y `<select>` de modelo con presets por proveedor
     (anthropic: `claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-8`;
     openai: `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`). Al cambiar de proveedor, si el
     modelo actual no aplica, salta al default de ese proveedor. Ambos van en el patch.

8. **Entorno / deps / docs**
   - `requirements.txt`: `openai>=1.40`.
   - `.env.example`, `docker-compose.yml`, `DEPLOY.md`: `OPENAI_API_KEY` con el mismo
     trato opcional que `ANTHROPIC_API_KEY` (sin key → solo-reglas en esa cuenta).
   - `config.yaml` / `config.docker.yaml`: `provider: anthropic` documentado bajo `ai:`,
     aclarando que el proveedor real se elige **por cuenta** en el panel.

## Manejo de errores

Sin cambios de contrato: cualquier fallo del proveedor (key faltante, timeout, respuesta
mal formada, modelo inexistente) cae a `AIVerdict(confirm=True, ai_used=False)` →  la
cuenta se comporta como el motor determinista. El veto solo afecta ejecución en `paper`.

## Seguridad

El payload a OpenAI lleva exactamente el mismo contexto numérico que a Anthropic (sin
keys, sin PII, sin el objeto `Position`). La key sale siempre del entorno
(`OPENAI_API_KEY`), nunca de `config.yaml` ni de la DB.

## Testing

- `tests/test_ai_advisor.py`: `OpenAIAdvisor` con fake client espejo
  (`chat.completions.create` → `choices[0].message.tool_calls[0].function.arguments`):
  parsea veredicto, usa el modelo configurado, cae a reglas ante error, no filtra
  secretos ni serializa `Position`.
- `tests/test_cli_ai.py`: `make_advisor` elige `OpenAIAdvisor`/`AnthropicAdvisor` por
  proveedor; `build_advisor` respeta `config.ai.provider`.
- `tests/test_store_accounts.py`: round-trip de `ai_provider`/`ai_model`.
- `tests/test_api_account_update.py`: PUT actualiza provider/model; rechaza proveedor
  inválido (422).
- `tests/test_fleet_hotreload.py`: `_config_sig` cambia con provider/model.
- `tests/test_config_ai.py`: `provider` default = `anthropic`.

## Fuera de alcance (YAGNI)

- `timeout_seconds` / `max_retries` por cuenta.
- Validación del string de modelo contra una lista fija en el backend.
- Otros proveedores (Gemini, etc.).
- Que la IA proponga lados u opere: sigue siendo veto-only.
