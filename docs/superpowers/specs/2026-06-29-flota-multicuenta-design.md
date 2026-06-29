# Flota multi-cuenta — Diseño

**Fecha:** 2026-06-29
**Estado:** propuesta para aprobación

## Objetivo

Correr **varias cuentas de paper trading en paralelo** (4-5), cada una con su **propia estrategia** y cadencia, todas filtradas por **Claude (veto de entradas)**, en **un solo contenedor / un solo proceso**, y poder **switchear y comparar las cuentas desde el panel web**.

## Decisiones clave (y por qué)

- **Un solo contenedor, un solo proceso.** FastAPI sirve el panel (estáticos) **y** la API **y** levanta la flota: cada cuenta corre en su propio hilo dentro del mismo proceso uvicorn. Sin nginx aparte, sin un contenedor por bot. Es lo más simple de deployar (lo que pidió el usuario: "todo en un mismo contenedor, no tan difícil").
- **DB agnóstica: SQLite por defecto, Postgres opcional vía `DATABASE_URL`.** Al ser un solo proceso, SQLite alcanza y deja todo self-contained (un contenedor, sin servicio de DB). La capa de datos se escribe con SQLAlchemy Core, así que apuntando `DATABASE_URL` a un Postgres gestionado de Coolify corre en Postgres sin cambiar código. Satisface "uno solo contenedor" y "usá Postgres si es mejor".
- **"PCR" = Price Action** (acción del precio), no Put/Call Ratio. Solo usa OHLCV — sin datos de opciones ni fuentes externas.
- **Claude = filtro de entradas (veto)**, igual que hoy. Barato y seguro; ya está implementado. Una llamada por señal de entrada, por cuenta. Necesita `ANTHROPIC_API_KEY`.
- **Las 5 cuentas corren simultáneas**; el panel deja elegir cuál ver y comparar todas.

## Arquitectura

```
┌──────────────────────────  UN contenedor / proceso  ──────────────────────────┐
│  uvicorn → FastAPI                                                              │
│    ├── GET /                → sirve el panel (SPA buildeada, StaticFiles)        │
│    ├── GET /api/...         → API (account-aware)                                │
│    └── startup: Fleet.start()                                                    │
│          ├── hilo cuenta "scalper"   → loop EMA/RSI   (1m / 12s)  → Store        │
│          ├── hilo cuenta "macd"      → loop MACD      (5m / 30s)  → Store        │
│          ├── hilo cuenta "bollinger" → loop Bollinger (15m / 60s) → Store        │
│          ├── hilo cuenta "breakout"  → loop Breakout  (30m / 2m)  → Store        │
│          └── hilo cuenta "price"     → loop PriceAct. (1h / 3m)   → Store        │
│                                                                                  │
│  Store (SQLAlchemy Core)  ── DATABASE_URL ──►  SQLite (volumen)  | Postgres      │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Fleet:** orquestador que, al arrancar la app, lanza un hilo *daemon* por cuenta. Cada hilo construye su `Engine` (estrategia, riesgo, timeframe, feed, advisor) desde la config de esa cuenta y corre su `run_loop` con su intervalo. Aislamiento de fallos por cuenta (una cuenta que tira excepción no frena a las otras). Cierre limpio en shutdown.
- **Feed:** cada cuenta tiene su `CcxtDataFeed` (con `enableRateLimit`). Volumen de requests modesto (5 cuentas, intervalos de 12s a 3min).
- **Un solo proceso → SQLite seguro:** acceso multi-hilo con `check_same_thread=False` + pool de SQLAlchemy. No hay el problema de multi-escritor entre procesos que motivaba Postgres.
- **uvicorn con un solo worker** (`--workers 1`): la flota se levanta una sola vez. Con varios workers se duplicarían los hilos de las cuentas (cada cuenta operaría N veces). Para escalar la API en el futuro: separar la flota a su propio proceso/entrypoint.

## Modelo de datos (scoping por cuenta)

Todas las tablas existentes suman una columna `account TEXT NOT NULL`:

- `decisions(account, ts, symbol, action, reason, ema_fast, ema_slow, rsi, ai_action, ai_confidence, ai_rationale, ...)`
- `fills(account, ts, symbol, side, quantity, price, fee)`
- `positions(account, symbol, ...)` — PK compuesta `(account, symbol)`
- `equity(account, ts, equity, cash)`

Nueva tabla `accounts` (metadata + estado configurable desde la web):

```
accounts(
  id TEXT PRIMARY KEY,        -- "scalper", "macd", ...
  name TEXT,                  -- "Scalper EMA/RSI"
  strategy TEXT,              -- "ema_rsi" | "macd" | "bollinger" | "breakout" | "price_action"
  symbol TEXT,                -- "BTC/USDT"
  timeframe TEXT,             -- "1m"
  interval_seconds INT,       -- 12
  starting_cash REAL,         -- 10000
  ai_enabled BOOL,            -- true
  enabled BOOL,               -- la cuenta corre o está pausada
  params JSON                 -- parámetros de la estrategia (fast/slow, etc.)
)
```

La capa `Store` recibe `account` en cada método (`record_decision(account, ...)`, `recent_decisions(account, limit)`, etc.). SQLAlchemy Core para que el mismo SQL corra en SQLite y Postgres.

## Estrategias (pluggables)

Interfaz común (la actual `decide(df, params) -> Signal` ya es pura):

```python
class Strategy(Protocol):
    name: str
    def decide(self, df: pd.DataFrame, params: dict) -> Signal: ...
```

Registro por nombre → cada cuenta elige su `strategy`. Lineup:

1. **EMA/RSI** (`ema_rsi`) — tendencia. Ya existe. Cruce de EMAs + filtro RSI.
2. **MACD** (`macd`) — momentum. Señal por cruce MACD/signal y/o histograma.
3. **Bollinger** (`bollinger`) — reversión a la media. Compra cerca de banda inferior, vende cerca de la superior/media.
4. **Breakout Donchian** (`breakout`) — ruptura de rango. Compra al romper el máximo de N velas, sale al perder el mínimo.
5. **Price Action** (`price_action`) — patrones de vela + estructura. Señales por engulfing / pin bar en swing highs/lows y rupturas de soporte/resistencia. Solo OHLCV.

Cada estrategia: TDD, función pura, testeada con velas sintéticas. El riesgo (stop/take/sizing) y el veto de Claude son comunes a todas (no se reimplementan).

## Cadencias (timeframe · intervalo de chequeo)

| Cuenta | Estrategia | Timeframe | Intervalo | Razón |
|---|---|---|---|---|
| Scalper | EMA/RSI | 1m | 12 s | ruido rápido, ciclos cortos |
| Momentum | MACD | 5m | 30 s | tendencias intradía |
| Reversión | Bollinger | 15m | 60 s | rangos, sin apuro |
| Ruptura | Breakout Donchian | 30m | 2 min | rupturas más lentas |
| Acción del precio | Price Action | 1h | 3 min | estructura de mayor marco |

(El intervalo siempre << timeframe: chequea salidas seguido, pero la decisión se actualiza por vela cerrada. Editable por cuenta desde la web.)

## IA (Claude) — veto por cuenta

Reusa el `AIAdvisor` actual (veto-only de entradas, fail-safe a reglas). `ai_enabled` por cuenta. Sin `ANTHROPIC_API_KEY` cae a solo-reglas (no rompe). El panel muestra el veredicto de Claude por entrada (ya soportado en `LiveAnalysis`).

## API (account-aware)

- `GET /api/accounts` → lista de cuentas con resumen (estrategia, equity, P&L, posición abierta, última corrida).
- Los endpoints existentes toman `?account=<id>` (default: la primera): `/api/status`, `/api/equity`, `/api/positions`, `/api/decisions`, `/api/fills`, `/api/candles`.
- `PUT /api/accounts/{id}` → editar config de una cuenta (estrategia/params/timeframe/intervalo/IA/enabled) y aplicarla (el hilo de esa cuenta relee y se reconfigura). [Fase 4]

## Panel web (multi-cuenta)

- **Selector de cuenta** en la barra superior (switchear cuál ver).
- **Tablero comparativo**: curvas de equity de todas las cuentas superpuestas + ranking por P&L (leaderboard).
- **Vista por cuenta**: la vista en vivo que ya construimos (precio, próxima corrida, análisis, decisión/IA), scoped a la cuenta elegida.
- **Config por cuenta** (switchear/tunear estrategia y cadencia desde la web). [Fase 4]

## Fases (cada una deja software andando)

1. **Datos** — `Store` con SQLAlchemy Core + columna `account` + tabla `accounts`. SQLite default, Postgres vía `DATABASE_URL`. Migración del esquema. La cuenta única actual sigue funcionando como `account="default"`.
2. **Estrategias** — interfaz pluggable + registro; implementar MACD, Bollinger, Breakout, Price Action (TDD). EMA/RSI se adapta a la interfaz.
3. **Flota + un contenedor** — orquestador de hilos por cuenta; FastAPI sirve el panel estático y arranca la flota en startup; Dockerfile/compose colapsados a un solo servicio; config de cuentas (semilla de las 5).
4. **Panel multi-cuenta** — selector, comparativa/ranking, API account-aware, edición de config por cuenta.

## Testing

- Estrategias: tests puros con velas sintéticas (cada patrón de señal).
- Store: tests sobre SQLite en memoria; round-trip por `account`; aislamiento entre cuentas.
- Fleet: test de que lanza N hilos, aísla fallos por cuenta, y corta limpio.
- API: TestClient con `?account=`; `/api/accounts`.
- Frontend: vitest de los componentes nuevos (selector, comparativa).

## Riesgos / decisiones abiertas

- **SQLite multi-hilo:** un solo proceso lo hace seguro; usar pool + `check_same_thread=False`. Si en el futuro se quiere multi-proceso, ya está Postgres por `DATABASE_URL`.
- **Rate limits de OKX:** 5 feeds independientes con `enableRateLimit`; intervalos holgados. Monitorear; si molesta, compartir un feed por símbolo.
- **Costo IA:** 5 cuentas × llamadas por entrada. Con Haiku es bajo; `ai_enabled` por cuenta permite apagar las que no la necesiten.
- **Price Action:** definición acotada para v1 (engulfing + pin bar en swings + ruptura S/R). No es "IA de chartismo"; son reglas claras y testeables.
- **Migración de datos:** la DB actual (`americo.sqlite`) pasa a tener `account`; las filas viejas se etiquetan `default`.
```
