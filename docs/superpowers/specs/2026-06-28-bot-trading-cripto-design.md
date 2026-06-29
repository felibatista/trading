# Plan: Bot de trading cripto (paper → real) con panel y capa de IA opcional

- **Fecha:** 2026-06-28
- **Proyecto:** AMÉRICO — bot de auto-trading cripto en simulación realista
- **Estado:** Diseño acordado en brainstorming. Listo para pasar a plan de implementación.

---

## 1. Objetivo y filosofía

Aprender trading algorítmico **construyendo** un bot real que opera primero en
**simulación sin riesgo**, con la arquitectura lista para pasar a dinero real el día
que la estrategia lo justifique.

Principios que ordenan todo el diseño:

- **Honestidad ante todo.** La mayoría de los traders minoristas pierde dinero. El bot
  es un vehículo de aprendizaje y disciplina (estrategia explícita + gestión de riesgo),
  no una máquina de generar dinero.
- **La lógica determinística manda.** Las reglas/indicadores son la fuente de verdad.
  La IA explica y filtra; nunca es el único decisor (al menos en v1).
- **Paper → real sin reescribir.** Las piezas se separan por interfaces para que pasar de
  simulación a real sea cambiar una implementación, no el código de estrategia.

## 2. Alcance v1 y no-objetivos

**En alcance:**

- Mercado: **cripto spot** (sin apalancamiento).
- 1–3 pares (BTC/USDT, ETH/USDT).
- **Timeframe configurable** (`1d`, `4h`, `1h`, `15m`) → cubre decisiones diarias e intradía con el mismo código.
- **Simulación realista** sobre **datos de producción reales**.
- Estrategia base de reglas (EMA + RSI) + gestión de riesgo.
- **Capa de IA opcional**, enchufable y **apagada por defecto**.
- **Panel web** (tema claro, estética shadcn) para monitoreo.
- Backtesting + forward-test.
- Despliegue **24/7 en VPS Linux** (Docker).

**No-objetivos (YAGNI por ahora):**

- Perpetuos / apalancamiento / márgenes (fase posterior).
- Multi-exchange simultáneo (sí dejamos la abstracción CCXT para cambiar fácil).
- Alta frecuencia (segundos).
- Que la IA opere con dinero real de forma autónoma.
- ML/optimización pesada de hiperparámetros.

## 3. Decisiones clave (stack)

Resultado de la investigación multi-fuente (ver `docs/`/research):

| Capa | Elección | Por qué |
|---|---|---|
| Lenguaje | **Python** | Estándar del trading algorítmico; ecosistema rico |
| Datos + ejecución | **CCXT** | Interfaz única para >100 exchanges; misma firma en demo y real |
| Simulación realista | **OKX Demo Trading** (`set_sandbox_mode(True)`) | Datos de **producción reales** + fills contra **libro real**; no se resetea como un testnet aislado |
| Alternativa exchange | **Bybit Demo** (apuntar a `api-demo.bybit.com`) | Detrás de la misma interfaz CCXT |
| Datos para señales | CCXT público (sin API key) | OHLCV/ticker/order book reales y gratis |
| Indicadores | pandas + pandas-ta | Cálculo de EMA/RSI/ATR sobre OHLCV |
| Backtest histórico | **vectorbt** | Rápido; acepta fees y slippage explícitos |
| Scheduler | APScheduler (o cron del VPS) | Dispara el ciclo según timeframe |
| IA (opcional) | SDK `anthropic` (Claude **Haiku** por defecto) | Razona/explica; barato; configurable |
| Persistencia | SQLite (DB **separada** paper vs real) | Simple; migrable a Postgres |
| Infra | VPS Linux + Docker, IP estática, env vars | 24/7, evita bans/rate-limits |
| Panel | Web app, tema claro, shadcn (diseño en Pencil) | UX clara, datos legibles |

## 4. Arquitectura y componentes

Interfaces (abstracciones) que hacen que **paper → real** sea un cambio de implementación:

- **`DataFeed`** — obtiene OHLCV / ticker / order book (CCXT público).
- **`Strategy`** — recibe datos + indicadores; emite señal `BUY | SELL | HOLD` + metadata (qué indicadores la dispararon).
- **`AIAdvisor`** *(opcional)* — recibe el contexto de la señal y devuelve `{ acción, confianza, rationale }`. Implementación **passthrough** (no-op) cuando está apagada.
- **`RiskManager`** — valida y ajusta: tamaño de posición, stop-loss/take-profit, exposición máxima, máx % por trade, circuit breaker.
- **`Broker`** — `PaperBroker` (OKX Demo) | `LiveBroker` (OKX real). **Misma firma** (`create_order`, `fetch_balance`, …).
- **`Runner/Scheduler`** — dispara el ciclo según el timeframe; loop persistente 24/7.
- **`Store`** — persiste portfolio, posiciones, trades, decisiones (+ rationale), logs.
- **`Backtester`** — replay histórico con vectorbt.
- **`API` (FastAPI)** — expone el estado al panel.

**Flujo de una decisión:**

```
DataFeed → indicadores → Strategy(señal) → AIAdvisor(opcional: confirma/explica)
        → RiskManager(sizing + SL/TP + límites) → Broker(orden paper)
        → Store(trade + rationale + log) → API → Panel
```

## 5. Estrategia inicial (reglas, configurable)

Punto de partida simple y sólido para aprender (no es consejo financiero):

- **Entrada (long-only en spot):** EMA rápida (ej. 20) cruza **por encima** de la EMA lenta (ej. 50) **y** RSI saliendo de sobreventa (filtro de momentum).
- **Salida:** cruce inverso de EMAs, o RSI en sobrecompra (> 70), o el stop-loss / take-profit del `RiskManager`.
- Todo **parametrizable** en config (periodos, umbrales, pares, timeframe).
- Nada va a paper hasta validar en backtest; nada va a real hasta consistencia en forward-test.

## 6. Gestión de riesgo (lo más importante)

- **Riesgo por trade:** máx **1%** del equity (configurable).
- **Tamaño de posición** derivado de la distancia al stop (no monto fijo).
- **Stop-loss obligatorio** en cada entrada (ATR-based o % fijo).
- Take-profit / trailing opcional.
- **Exposición total máx** (ej. 30% del equity en mercado a la vez).
- Máximo de posiciones simultáneas.
- **Circuit breaker:** si el drawdown diario supera X% → el bot se pausa.
- Nunca promediar a la baja sin una regla explícita.

## 7. Capa de IA (Claude) — opcional, apagada por defecto

- **Rol:** razonar/explicar la señal en lenguaje natural y actuar como **filtro auxiliar** (confirmar o vetar con justificación). No genera alfa por sí sola.
- **Modelo por defecto:** Haiku (barato); configurable a Sonnet/Opus.
- **Entrada:** contexto **numérico** (indicadores, régimen, riesgo, posición). **Nunca** claves ni datos sensibles en el prompt.
- **Salida estructurada:** `{ acción, confianza, rationale }`. La lógica determinística sigue siendo la fuente de verdad; en v1 la IA **no** puede forzar una operación en real.
- **Costo:** centavos/mes a frecuencia diaria; se activa con un switch en config.
- **Guardrails:** timeouts, fallback a solo-reglas si la IA falla, sin decisiones de dinero real por IA al inicio.

## 8. Datos y ejecución: paper → real

- **Paper:** OKX Demo — datos de producción reales, fills contra libro real, saldo virtual, sin KYC.
- **Real (fase posterior):** `set_sandbox_mode(False)` + keys reales (KYC), DB separada, revalidar min-notional / lot-size / fees / rate limits.
- Toda la ejecución pasa por CCXT → cambiar de exchange casi sin tocar código.
- **Pitfalls a cubrir:** los *testnets* aislados se resetean (por eso usamos **Demo**, no testnet); `set_sandbox_mode` de Bybit requiere apuntar a `api-demo` a mano; respetar `enableRateLimit`; IP estática en el VPS; el slippage del demo es **optimista** → aplicar slippage conservador en el backtest.

## 9. Persistencia y estado

- SQLite en v1 (Postgres a futuro). **DB separada** para trades paper vs real.
- Tablas: `trades`, `positions`, `decisions` (señal + rationale IA), `equity_snapshots`, `logs`.

## 10. Ejecución 24/7

- VPS Linux + Docker. Runner persistente con APScheduler; reconexión de websockets; reintentos; logging estructurado.
- **Forward-test mínimo ~30 días** en demo antes de evaluar el paso a real.

## 11. Panel / dashboard

- Web app, **tema claro**, estética **shadcn**. Diseño en Pencil (`pencil-new.pen`).
- **Muestra:** estado del bot (PAPER/real, exchange, timeframe, próxima corrida, uptime), KPIs (equity, P&L hoy/total, win rate), gráfico precio/equity, **tarjeta "Decisión de Américo"** (señal + indicadores + rationale de la IA), posiciones abiertas, historial de trades, registro de actividad, exposición/riesgo.
- **Controles:** start/stop, modo paper/real, timeframe, IA on/off, configuración.
- **Backend:** FastAPI expone el estado; el front lo consume.

## 12. Backtesting y validación

- **vectorbt** para backtest histórico con fees + slippage conservador.
- Métricas: retorno, drawdown máx, win rate, Sharpe, nº de trades.
- **Forward-test** en demo ~30 días.
- Criterio: no pasar a real hasta lograr consistencia en paper.

## 13. Seguridad

- Claves **nunca** en el repo; env vars / `config-private` separada.
- Keys reales con permiso de **trade pero SIN retiro**.
- DB paper y real separadas.
- Nunca claves en prompts de IA.

## 14. Estructura de carpetas propuesta

```
trading/
  bot/
    data/        DataFeed (CCXT)
    strategy/    estrategias + indicadores
    ai/          AIAdvisor + prompts
    risk/        RiskManager
    broker/      PaperBroker, LiveBroker
    runner/      scheduler + loop
    store/       persistencia (SQLite)
    backtest/    vectorbt
    config/      config.yaml, .env.example
  api/           FastAPI para el panel
  web/           panel front (shadcn, tema claro)
  design/        pencil-new.pen
  docs/
```

## 15. Roadmap por fases

- **Fase 0** — Scaffolding + config + `DataFeed` (datos reales) + un indicador; imprime la señal.
- **Fase 1** — `PaperBroker` (OKX Demo) + `RiskManager` + `Strategy` + `Store` + loop manual.
- **Fase 2** — `Scheduler` 24/7 + logging + `Backtester` (vectorbt).
- **Fase 3** — `API` (FastAPI) + Panel (shadcn) conectado a datos reales.
- **Fase 4** — Capa IA opcional (explicar/filtrar).
- **Fase 5** — Forward-test 30 días → evaluación → (opcional) preparación a real.

## 16. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobreajuste en backtest | Validación out-of-sample + forward-test |
| Slippage/latencia subestimados | Slippage conservador; empezar con tamaño mínimo |
| Bans / rate limits | `enableRateLimit`, IP estática, websockets |
| Caídas del demo | Manejo de reconexión; OKX/Bybit **Demo** (no testnet) |
| IA poco fiable | Solo-reglas como fuente de verdad; IA off por defecto |
| Riesgo emocional/financiero | No real hasta consistencia; solo dinero que se pueda perder |

## 17. Criterios de éxito (v1)

- El bot corre 24/7 en el VPS, decide según el timeframe configurable, opera en **paper con datos reales**, registra todo, y el panel muestra el estado con claridad.
- La capa de IA se puede prender/apagar sin tocar la lógica de estrategia.
- Backtest + forward-test funcionando; el camino a real está documentado.
