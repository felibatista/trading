# Backtesting de estrategias (reusando el motor real)

**Fecha:** 2026-06-29
**Estado:** aprobado (diseño)

## Contexto y objetivo

Hoy el bot hace *forward paper trading* en vivo: corre ciclos sobre datos en tiempo
real, sin replay histórico. No se puede comparar las 5 estrategias en igualdad de
condiciones ni tunear parámetros sin esperar tiempo real.

Objetivo: **backtesting** que replaya histórico (default **7 días**) de cada una de las 5
cuentas con su estrategia/timeframe/params reales, mide performance, y se ve desde un
**comando CLI** y desde una **sección "Backtest" en el panel** (con botón para iniciar,
configuración de fecha/rango, y vistas de los resultados).

Restricción clave del usuario: la **IA (veto) se usa SOLO en la cuenta `price_action`**,
con **OpenAI `gpt-4o-mini`**; las otras 4 corren en **solo-reglas**.

## Decisiones tomadas

- **Reusar el `Engine` real**, no reimplementar (evita el clásico "el backtest no
  coincide con producción").
- **Alcance:** las 5 cuentas de `DEFAULT_ACCOUNTS` con su strategy/timeframe/params.
- **IA:** veto solo en `price_action` (provider `openai`, modelo `gpt-4o-mini`),
  inyectable (tests usan stub determinístico, nunca la API real). Sin `OPENAI_API_KEY`
  cae a solo-reglas (costo $0, no rompe). Costo real estimado: centavos por corrida.
- **SL/TP:** a `close` (igual que live), para que el backtest prediga lo que el bot
  realmente hace. Modo intrabar (high/low) queda fuera de alcance.
- **Salida:** CLI (tabla) **y** panel (sección con botón + rango de fechas + tabla de
  métricas + curva de equity).
- **API del panel:** endpoint **síncrono** con **cache de velas en proceso** (la primera
  corrida baja OHLCV de OKX; las siguientes son rápidas). Job en background queda fuera de
  alcance (v1).
- **Ventana configurable:** el panel manda `from`/`to` (default últimos 7 días); la CLI
  acepta `--days` (default 7) y opcionalmente `--from`/`--to`.

## Arquitectura

```
load_ohlcv_range(exchange, symbol, tf, since, until)   # fetch paginado + warmup
        │  (DataFrame completo, sin look-ahead garantizado por el replay)
        ▼
HistoricalFeed(df)  ──►  Engine.run_cycle()  (MISMO código que en vivo)
        ▲                   │  Store(:memory:) · LocalPaperBroker(fee, slippage)
   cursor k=warmup..N-1     │  decider=get_strategy(acc.strategy)
                            │  advisor = OpenAIAdvisor(gpt-4o-mini) solo si price_action
                            ▼
        equity_series / fills / decisions  ──►  metrics  ──►  BacktestResult
```

### Componentes (módulos nuevos en `bot/backtest/`)

1. **`data.py` — fetch histórico paginado**
   `load_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms, warmup_bars=200)`.
   Loop sobre `exchange.fetch_ohlcv(symbol, timeframe, since=…, limit=max)` avanzando
   `since` por el timestamp de la última vela + 1, hasta cubrir `until`. Dedup por
   timestamp, orden ascendente, descarta la vela en formación final. Pide `warmup_bars`
   extra **antes** de `since` para que los indicadores estén calientes en la primera vela
   operable. Respeta `enableRateLimit` de ccxt. Helper `timeframe_to_ms(tf)`.

2. **`feed.py` — `HistoricalFeed` (implementa `DataFeed`)**
   Tiene el DataFrame completo + un cursor `k`. `fetch_ohlcv(symbol, tf, limit)` devuelve
   `df.iloc[: k + 1].tail(limit)`. El `Engine` ya hace `drop_forming_candle`, así que la
   vela `k` actúa como **vela en formación** (se descarta) y la decisión/precio salen de
   la vela cerrada `k-1` → **semántica idéntica a live, sin look-ahead**. Método
   `set_cursor(k)`.

3. **`metrics.py` — funciones puras**
   - `total_return_pct(curve)`, `max_drawdown_pct(curve)`, `exposure(decisions|positions)`.
   - `closed_trades(fills)` → empareja BUY→SELL (FIFO, 1 símbolo por cuenta) y da PnL por
     trade; de ahí `win_rate` y `num_trades`.
   - `equity_curve` = `equity_series` del store (lista de `{ts, equity, cash}`).

4. **`runner.py` — orquestación**
   - `run_backtest(account, candles, *, risk, advisor=None, fee, slippage, cash, symbol)
     -> BacktestResult`: arma `Store(:memory:)`, `LocalPaperBroker`, `HistoricalFeed`,
     `Engine(...)`; loop `k` de `warmup` a `len-1` (`feed.set_cursor(k)`,
     `engine.run_cycle(symbol)`); calcula métricas. `ai_affects_execution=True` cuando hay
     advisor (es "paper", el veto afecta la ejecución y por eso se puede medir su efecto).
   - `run_fleet_backtest(accounts, candles_by_account, *, config, ai_account="price_action",
     ai_provider="openai", ai_model="gpt-4o-mini", advisor_factory=make_advisor)
     -> list[BacktestResult]`: corre las 5; arma el advisor (vía `advisor_factory`, **inyectable**)
     solo para `ai_account`, el resto `advisor=None`.
   - `BacktestResult` = dataclass: `account_id, name, strategy, ai`, métricas
     (`return_pct, max_drawdown_pct, win_rate, num_trades, final_equity, exposure`),
     `equity_curve`, `trades`.

5. **CLI — `bot backtest`** (subcomando nuevo en `bot/cli.py`)
   `python -m bot backtest [--days 7] [--from ISO] [--to ISO] [--symbol BTC/USDT]
   [--exchange okx] [--config config.yaml]`. Baja datos una vez por timeframe presente,
   corre las 5 (IA solo en price_action), imprime tabla ordenada por retorno:
   `estrategia | retorno% | maxDD% | win% | #trades | equity final | IA`.

6. **API — `POST /api/backtest`** (`api/app.py` + modelos en `api/models.py`)
   Body `BacktestRequest{ from?: str, to?: str, days?: int = 7, symbol?: str }`.
   Resuelve la ventana, baja OHLCV con **cache en proceso** keyed por
   `(symbol, timeframe, since, until)`, corre `run_fleet_backtest`, devuelve
   `list[BacktestResultOut]` (métricas + `equity_curve`). Síncrono. El feed/exchange y el
   `advisor_factory` son **inyectables** para tests (dependency override).

7. **Panel — sección "Backtest"** (`web/src/`)
   - `lib/types.ts`: `BacktestResult` + `BacktestRequest`.
   - `lib/api.ts`: `runBacktest(req)`.
   - Nueva tab/sección **"Backtest"** con:
     - **Configuración de fecha:** inputs `from`/`to` (date pickers), default últimos 7 días,
       más atajos (7d / 14d / 30d).
     - **Botón "Correr backtest"** con estado de carga (spinner; aviso de que la 1ª corrida
       baja datos y puede tardar ~30–60s).
     - **Vistas de datos:** tabla de métricas por estrategia (ordenada por retorno, con
       color por signo) + **gráfico de curva de equity** comparando las 5 (recharts, estilo
       `ComparisonChart`). Badge "IA" en la fila de price_action.

### Manejo de errores

- Fetch: si OKX falla/timeout, el endpoint/CLI devuelve error claro (no cuelga); reintentos
  acotados vía ccxt. Si una cuenta no tiene datos suficientes, su resultado es vacío
  (return 0, 0 trades), no rompe la corrida de las demás.
- IA: el fail-safe del advisor ya cae a reglas ante cualquier error/sin key.

### Seguridad / costo

- La IA manda el mismo contexto numérico que en vivo (sin secretos/PII). Key de
  `OPENAI_API_KEY` del entorno. Costo estimado: **~$0.002–$0.02 por corrida** (gpt-4o-mini,
  veto solo en entradas de price_action en 1h).

## Testing

- `test_backtest_metrics.py`: `total_return_pct`, `max_drawdown_pct`, `closed_trades` /
  `win_rate` con curvas y fills conocidos.
- `test_backtest_feed.py`: `HistoricalFeed` devuelve los slices correctos y respeta la
  vela-en-formación (no look-ahead).
- `test_backtest_data.py`: paginación con un **fake exchange** que devuelve OHLCV en
  chunks (sin red); dedup, orden, warmup.
- `test_backtest_runner.py`: end-to-end **determinístico** con dataset sintético chico +
  **stub advisor** (caso IA-veta y caso sin-IA) → #trades/equity esperados; verifica que el
  veto solo se aplica a la cuenta con IA.
- `test_api_backtest.py`: `TestClient` con feed + advisor_factory inyectados → JSON de
  métricas y curva; valida default 7 días y `from/to`.
- Web: `tsc` (no hay infra de component tests); helpers nuevos con test si aplica.

## Fuera de alcance (YAGNI)

- SL/TP intrabar (high/low).
- IA en estrategias distintas de price_action.
- Job en background / cola para el endpoint (síncrono + cache alcanza para v1).
- Barrido/optimización de parámetros (grid search) — futura iteración.
- Persistir resultados de backtest en la DB (se calculan on-demand).
- Métricas avanzadas (Sharpe, profit factor) — se pueden sumar después.
