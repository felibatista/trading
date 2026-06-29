# Fase 3 — API + Panel web — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exponer el estado del bot AMÉRICO (decisiones, fills, posiciones, equity) a través de una **API FastAPI** de solo lectura sobre la misma SQLite, y construir un **panel web** (Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts) que la consulta en vivo (polling) y la muestra con el layout claro ya diseñado en Pencil.

**Architecture:** El bot (Fases 0–1) persiste su estado en `americo.sqlite` vía la clase `Store` (`bot/store/db.py`). Esta fase **no toca la lógica de trading**: agrega (a) dos métodos de lectura al `Store` (`equity_series`, `recent_fills`) más una extensión aditiva de `recent_decisions`; (b) un backend `api/` (FastAPI) que abre el mismo `Store` en modo lectura y publica endpoints JSON con modelos Pydantic y CORS; (c) un frontend `web/` que hace polling de esos endpoints y los renderiza. El backend es 100% testeable con `pytest` + `fastapi.testclient.TestClient` sobre un `Store` temporal en memoria sembrado con filas (sin red). Las utilidades puras del frontend se testean con `vitest` (TDD); los componentes de UI se verifican con `npm run build` / `npm run dev`.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, httpx (test client), Pydantic (ya viene con FastAPI), `sqlite3` (stdlib, vía el `Store` existente), `pytest`. Frontend: Node 18+, Vite, React 18, TypeScript, Tailwind CSS v3, shadcn/ui (primitivas copiadas), Recharts, lucide-react, Radix Tabs, vitest.

## Estado asumido (precondiciones)

Este plan asume que **Fase 1 ya está implementada** y que existen en el repo:
- `bot/store/db.py` con la clase `Store(path=":memory:")` y los métodos **de escritura** `record_decision(ts,symbol,action,reason,ema_fast,ema_slow,rsi)`, `record_fill(ts, fill: Fill)`, `upsert_position(pos: Position, opened_at)`, `record_equity(ts,equity,cash)`, y **de lectura** `recent_decisions(limit) -> list[dict]` (más reciente primero), `get_positions() -> dict[str, Position]`, `latest_equity() -> tuple[float,float] | None`.
- `bot/config.py` con `Config` exponiendo `exchange`, `timeframe`, `symbols`, `db_path`, `broker` (con `.kind` ∈ {"paper","okx_demo"}, `.paper_cash`, …) y `risk.*`; más `BrokerParams`.
- `bot/broker/models.py` con `Fill`, `Position`, `Side` (usados solo para **sembrar** datos en los tests del backend).

Si alguna de estas piezas no estuviera presente, completá primero la Fase 1 (ver `docs/superpowers/plans/2026-06-28-fase1-motor-paper.md`).

## Global Constraints

- **Python `>=3.11`.**
- **Nuevas dependencias de backend** en `requirements.txt`: `fastapi`, `uvicorn[standard]`, `httpx` (este último para `TestClient`). Instalar con el venv del proyecto.
- **El backend lee el `Store` existente en modo solo-lectura.** No escribe en la DB ni importa el motor/broker en runtime (solo importa `Fill/Position/Side` en los **tests**, para sembrar fixtures).
- **Tests de backend sin red:** usan `fastapi.testclient.TestClient` sobre un `Store(":memory:")` temporal sembrado con filas y `app.dependency_overrides`. Ningún test llama a un exchange ni abre un socket externo.
- **El bot no persiste un flag de "corriendo".** El pill verde "Operando" y el ámbar "PAPER" se **derivan de la config** (`broker_kind`), no de un estado real. Esto es una simplificación explícita de la fase.
- **Frontend** en `web/`: Vite + React + TypeScript + Tailwind CSS + shadcn/ui + Recharts. **Node 18+.**
- **Tema claro shadcn** acorde al diseño de Pencil: base neutra **zinc**, acento **emerald**, semántica **verde/rojo** para P&L, números **monoespaciados con `tabular-nums`**, tarjetas blancas con bordes sutiles.
- **Identificadores y mensajes de commit en inglés;** textos visibles al usuario (labels, mensajes) en **español**.
- **Comandos Windows:** backend `.venv/Scripts/python.exe -m pytest -q` y `.venv/Scripts/python.exe -m uvicorn api.app:app --reload`; frontend (desde `web/`) `npm install`, `npm run build`, `npm run dev`, `npx vitest run`.
- **Cada commit termina con el trailer** (segundo `-m`): `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## File Structure

| Archivo | Responsabilidad | Task |
|---|---|---|
| `requirements.txt` (modificar) | + `fastapi`, `uvicorn[standard]`, `httpx` | 1 |
| `api/__init__.py` | paquete (vacío) | 1 |
| `api/app.py` | `create_app()` FastAPI: health, endpoints, CORS | 1,4,5,6 |
| `api/deps.py` | `get_config`, `get_store` (DI, solo lectura) | 4 |
| `api/models.py` | modelos Pydantic de respuesta | 3 |
| `bot/store/db.py` (modificar) | + `equity_series`, `recent_fills`, `close`; extender `recent_decisions` | 2 |
| `tests/test_api_health.py` | health vía `TestClient` | 1 |
| `tests/test_store_reads.py` | tests de los métodos de lectura nuevos | 2 |
| `tests/test_api_models.py` | tests de los modelos Pydantic | 3 |
| `tests/test_api_endpoints.py` | tests de endpoints + CORS (Store sembrado) | 4,5,6 |
| `web/` (Vite scaffold) | package.json, vite/ts/tailwind/postcss config, index.html | 7 |
| `web/src/index.css`, `web/src/main.tsx`, `web/src/App.tsx` | bootstrap + layout raíz | 7,9 |
| `web/src/lib/utils.ts` | `cn()` | 7 |
| `web/src/components/ui/*` | primitivas shadcn (button, card, badge, table, tabs) | 7 |
| `web/src/lib/types.ts` | tipos TS espejo de los modelos | 8 |
| `web/src/lib/api.ts` | cliente fetch tipado | 8 |
| `web/src/lib/format.ts` | utilidades puras (formatters, derivados) | 8 |
| `web/src/lib/format.test.ts` | tests vitest de `format.ts` | 8 |
| `web/src/lib/use-polling.ts` | hook `usePolling` | 8 |
| `web/src/components/{TopBar,KpiRow,EquityChart,DecisionCard,PositionsTable,HistoryTable,ActivityLog}.tsx` | componentes del panel | 9 |

---

### Task 1: Dependencias de backend + paquete `api/` + endpoint de salud (TDD)

**Files:**
- Modify: `requirements.txt`
- Create: `api/__init__.py` (vacío), `api/app.py`
- Test: `tests/test_api_health.py`

**Interfaces:**
- Produces: `api.app.create_app() -> FastAPI` y la instancia módulo-nivel `api.app.app`. Endpoint `GET /api/health -> {"status": "ok"}`.

- [ ] **Step 1: Agregar dependencias** — añadir al final de `requirements.txt`:

```
fastapi>=0.110
uvicorn[standard]>=0.29
httpx>=0.27
```

- [ ] **Step 2: Instalar** — Run: `.venv/Scripts/python.exe -m pip install -r requirements.txt`
Expected: instala `fastapi`, `uvicorn`, `httpx` (y sus deps) sin tocar lo ya presente.

- [ ] **Step 3: Crear `api/__init__.py`** (archivo vacío).

- [ ] **Step 4: Escribir el test que falla** — `tests/test_api_health.py`:

```python
from fastapi.testclient import TestClient

from api.app import app


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_health.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'api.app'`.

- [ ] **Step 6: Implementar `api/app.py`:**

```python
from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="AMÉRICO API", version="1.0.0")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 7: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_health.py -q`
Expected: PASS (1 passed).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt api/__init__.py api/app.py tests/test_api_health.py
git commit -m "feat: add FastAPI backend package with health endpoint" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Métodos de lectura del `Store` (`equity_series`, `recent_fills`, `close`) + extender `recent_decisions` (TDD)

**Files:**
- Modify: `bot/store/db.py`
- Test: `tests/test_store_reads.py`

**Interfaces:**
- Produces (en `Store`):
  - `equity_series(self, limit: int = 200) -> list[dict]` — los últimos `limit` snapshots de equity en orden **cronológico (más viejo→más nuevo)**; cada dict con claves `ts`, `equity`, `cash`.
  - `recent_fills(self, limit: int = 50) -> list[dict]` — los últimos `limit` fills, **más reciente primero**; claves `ts`, `symbol`, `side`, `quantity`, `price`, `fee`.
  - `close(self) -> None` — cierra la conexión sqlite (para el ciclo de vida por request de la API).
- Modify: `recent_decisions(self, limit=10) -> list[dict]` — **extender** el `SELECT` para incluir también `ema_fast`, `ema_slow`, `rsi` (cambio aditivo: los callers existentes leen por nombre de clave y no se ven afectados; lo necesita la tarjeta "Decisión de Américo").

- [ ] **Step 1: Escribir el test que falla** — `tests/test_store_reads.py`:

```python
from bot.broker.models import Fill, Side
from bot.store.db import Store


def _seed_equity(s: Store) -> None:
    s.record_equity("2024-01-01T00:00:00+00:00", 10000.0, 10000.0)
    s.record_equity("2024-01-01T01:00:00+00:00", 10100.0, 9000.0)
    s.record_equity("2024-01-01T02:00:00+00:00", 10250.0, 9000.0)


def test_equity_series_oldest_to_newest_limited():
    s = Store(":memory:")
    _seed_equity(s)
    series = s.equity_series(limit=2)
    assert [p["equity"] for p in series] == [10100.0, 10250.0]  # últimos 2, cronológico
    assert series[0]["ts"] == "2024-01-01T01:00:00+00:00"
    assert set(series[0]) == {"ts", "equity", "cash"}


def test_equity_series_all_when_limit_large():
    s = Store(":memory:")
    _seed_equity(s)
    series = s.equity_series(limit=100)
    assert [p["equity"] for p in series] == [10000.0, 10100.0, 10250.0]


def test_recent_fills_newest_first():
    s = Store(":memory:")
    s.record_fill("t1", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05))
    s.record_fill("t2", Fill("BTC/USDT", Side.SELL, 0.5, 110.0, 0.055))
    fills = s.recent_fills(limit=10)
    assert len(fills) == 2
    assert fills[0]["side"] == "SELL"  # más reciente primero
    assert fills[0]["price"] == 110.0
    assert set(fills[0]) == {"ts", "symbol", "side", "quantity", "price", "fee"}


def test_recent_decisions_includes_indicators():
    s = Store(":memory:")
    s.record_decision("t1", "BTC/USDT", "BUY", "cruce alcista", 30.5, 29.0, 41.0)
    d = s.recent_decisions(limit=1)[0]
    assert d["action"] == "BUY"
    assert d["ema_fast"] == 30.5
    assert d["ema_slow"] == 29.0
    assert d["rsi"] == 41.0
```

- [ ] **Step 2: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_reads.py -q`
Expected: FAIL — `AttributeError: 'Store' object has no attribute 'equity_series'` (y `recent_fills`), más `KeyError: 'ema_fast'` en el test de decisiones.

- [ ] **Step 3: Extender `recent_decisions`** — en `bot/store/db.py`, dentro de `recent_decisions`, reemplazar la consulta:

```python
            "SELECT ts,symbol,action,reason FROM decisions ORDER BY id DESC LIMIT ?",
```

por:

```python
            "SELECT ts,symbol,action,reason,ema_fast,ema_slow,rsi FROM decisions"
            " ORDER BY id DESC LIMIT ?",
```

- [ ] **Step 4: Agregar los métodos nuevos** — en `bot/store/db.py`, dentro de la clase `Store` (por ejemplo, debajo de `latest_equity`):

```python
    def equity_series(self, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,equity,cash FROM equity ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def recent_fills(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,symbol,side,quantity,price,fee FROM fills"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 5: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_reads.py -q`
Expected: PASS (4 passed). Luego la suite completa: `.venv/Scripts/python.exe -m pytest -q` (todo verde; la extensión de `recent_decisions` es aditiva).

- [ ] **Step 6: Commit**

```bash
git add bot/store/db.py tests/test_store_reads.py
git commit -m "feat: add store read methods equity_series, recent_fills, close" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Modelos de respuesta Pydantic (TDD)

**Files:**
- Create: `api/models.py`
- Test: `tests/test_api_models.py`

**Interfaces:**
- Produces (todos `pydantic.BaseModel`):
  - `StatusResponse`: `exchange:str`, `timeframe:str`, `broker_kind:str`, `symbols:list[str]`, `equity:float`, `cash:float`.
  - `EquityPoint`: `ts:str`, `equity:float`, `cash:float`.
  - `PositionOut`: `symbol:str`, `quantity:float`, `entry_price:float`, `stop_loss:float`, `take_profit:float`.
  - `DecisionOut`: `ts:str`, `symbol:str`, `action:str`, `reason:str`, `ema_fast:float`, `ema_slow:float`, `rsi:float`.
  - `FillOut`: `ts:str`, `symbol:str`, `side:str`, `quantity:float`, `price:float`, `fee:float`.

- [ ] **Step 1: Escribir el test que falla** — `tests/test_api_models.py`:

```python
from api.models import DecisionOut, EquityPoint, FillOut, PositionOut, StatusResponse


def test_status_response_fields():
    s = StatusResponse(
        exchange="okx", timeframe="1h", broker_kind="paper",
        symbols=["BTC/USDT"], equity=10000.0, cash=9000.0,
    )
    assert s.broker_kind == "paper"
    assert s.symbols == ["BTC/USDT"]


def test_models_serialize():
    assert EquityPoint(ts="t", equity=1.0, cash=2.0).model_dump() == {
        "ts": "t", "equity": 1.0, "cash": 2.0,
    }
    assert PositionOut(
        symbol="BTC/USDT", quantity=1.0, entry_price=2.0, stop_loss=1.0, take_profit=3.0,
    ).symbol == "BTC/USDT"
    assert DecisionOut(
        ts="t", symbol="BTC/USDT", action="BUY", reason="x",
        ema_fast=1.0, ema_slow=2.0, rsi=3.0,
    ).action == "BUY"
    assert FillOut(
        ts="t", symbol="BTC/USDT", side="BUY", quantity=1.0, price=2.0, fee=0.1,
    ).side == "BUY"
```

- [ ] **Step 2: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_models.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'api.models'`.

- [ ] **Step 3: Implementar `api/models.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel


class StatusResponse(BaseModel):
    exchange: str
    timeframe: str
    broker_kind: str
    symbols: list[str]
    equity: float
    cash: float


class EquityPoint(BaseModel):
    ts: str
    equity: float
    cash: float


class PositionOut(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float


class DecisionOut(BaseModel):
    ts: str
    symbol: str
    action: str
    reason: str
    ema_fast: float
    ema_slow: float
    rsi: float


class FillOut(BaseModel):
    ts: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
```

- [ ] **Step 4: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_models.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add api/models.py tests/test_api_models.py
git commit -m "feat: add pydantic response models for the API" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: DI (`deps.py`) + endpoints `status` / `equity` / `positions` (TDD)

**Files:**
- Create: `api/deps.py`
- Modify: `api/app.py`
- Test: `tests/test_api_endpoints.py`

**Interfaces:**
- Produces:
  - `api.deps.get_config() -> Config` (lee `config.yaml`, ruta override por env `AMERICO_CONFIG`).
  - `api.deps.get_store(config) -> Iterator[Store]` (dependencia generadora: abre `Store(config.db_path)` y lo cierra en `finally`).
  - `GET /api/status -> StatusResponse` (de `Config` + `latest_equity()`; si no hay equity todavía → `equity=0.0, cash=0.0`).
  - `GET /api/equity?limit=N -> list[EquityPoint]` (default `limit=200`).
  - `GET /api/positions -> list[PositionOut]`.

- [ ] **Step 1: Escribir el test que falla** — `tests/test_api_endpoints.py`:

```python
import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.deps import get_config, get_store
from bot.broker.models import Fill, Position, Side
from bot.config import BrokerParams, Config
from bot.store.db import Store


@pytest.fixture
def client():
    store = Store(":memory:")
    store.record_equity("2024-01-01T00:00:00+00:00", 10000.0, 10000.0)
    store.record_equity("2024-01-01T01:00:00+00:00", 10120.0, 9000.0)
    store.record_fill("2024-01-01T01:00:00+00:00", Fill("BTC/USDT", Side.BUY, 0.01, 100.0, 0.001))
    store.upsert_position(
        Position("BTC/USDT", 0.01, 100.0, 98.0, 104.0), "2024-01-01T01:00:00+00:00"
    )
    store.record_decision(
        "2024-01-01T01:00:00+00:00", "BTC/USDT", "BUY", "cruce alcista", 30.5, 29.0, 41.0
    )

    cfg = Config(
        exchange="okx", timeframe="1h", symbols=["BTC/USDT"],
        broker=BrokerParams(kind="paper"),
    )

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_config] = lambda: cfg
    yield TestClient(app)
    app.dependency_overrides.clear()
    store.close()


def test_status_endpoint(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["exchange"] == "okx"
    assert body["timeframe"] == "1h"
    assert body["broker_kind"] == "paper"
    assert body["symbols"] == ["BTC/USDT"]
    assert body["equity"] == 10120.0  # latest_equity
    assert body["cash"] == 9000.0


def test_equity_endpoint_chronological(client):
    r = client.get("/api/equity?limit=10")
    assert r.status_code == 200
    series = r.json()
    assert [p["equity"] for p in series] == [10000.0, 10120.0]
    assert set(series[0]) == {"ts", "equity", "cash"}


def test_positions_endpoint(client):
    r = client.get("/api/positions")
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert pos[0]["symbol"] == "BTC/USDT"
    assert pos[0]["entry_price"] == 100.0
    assert pos[0]["stop_loss"] == 98.0
```

- [ ] **Step 2: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_endpoints.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'api.deps'` (error de colección al importar `get_config`/`get_store`).

- [ ] **Step 3: Implementar `api/deps.py`:**

```python
from __future__ import annotations

import os
from collections.abc import Iterator

from fastapi import Depends

from bot.config import Config, load_config
from bot.store.db import Store

CONFIG_PATH = os.environ.get("AMERICO_CONFIG", "config.yaml")


def get_config() -> Config:
    return load_config(CONFIG_PATH)


def get_store(config: Config = Depends(get_config)) -> Iterator[Store]:
    store = Store(config.db_path)
    try:
        yield store
    finally:
        store.close()
```

- [ ] **Step 4: Reemplazar `api/app.py`** por (agrega `status`/`equity`/`positions`; mantiene `health`):

```python
from __future__ import annotations

from fastapi import Depends, FastAPI

from api.deps import get_config, get_store
from api.models import EquityPoint, PositionOut, StatusResponse
from bot.config import Config
from bot.store.db import Store


def create_app() -> FastAPI:
    app = FastAPI(title="AMÉRICO API", version="1.0.0")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status", response_model=StatusResponse)
    def status(
        config: Config = Depends(get_config),
        store: Store = Depends(get_store),
    ) -> StatusResponse:
        eq = store.latest_equity()
        equity, cash = eq if eq is not None else (0.0, 0.0)
        return StatusResponse(
            exchange=config.exchange,
            timeframe=config.timeframe,
            broker_kind=config.broker.kind,
            symbols=config.symbols,
            equity=equity,
            cash=cash,
        )

    @app.get("/api/equity", response_model=list[EquityPoint])
    def equity(limit: int = 200, store: Store = Depends(get_store)) -> list[EquityPoint]:
        return [EquityPoint(**row) for row in store.equity_series(limit)]

    @app.get("/api/positions", response_model=list[PositionOut])
    def positions(store: Store = Depends(get_store)) -> list[PositionOut]:
        return [
            PositionOut(
                symbol=p.symbol,
                quantity=p.quantity,
                entry_price=p.entry_price,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
            )
            for p in store.get_positions().values()
        ]

    return app


app = create_app()
```

- [ ] **Step 5: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_endpoints.py tests/test_api_health.py -q`
Expected: PASS (4 passed: 3 nuevos + health).

- [ ] **Step 6: Commit**

```bash
git add api/deps.py api/app.py tests/test_api_endpoints.py
git commit -m "feat: add status, equity and positions endpoints" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Endpoints `decisions` / `fills` (TDD)

**Files:**
- Modify: `api/app.py`
- Test: `tests/test_api_endpoints.py` (agregar tests)

**Interfaces:**
- Produces:
  - `GET /api/decisions?limit=N -> list[DecisionOut]` (default `limit=20`, más reciente primero).
  - `GET /api/fills?limit=N -> list[FillOut]` (default `limit=50`, más reciente primero).

- [ ] **Step 1: Agregar los tests que fallan** — añadir a `tests/test_api_endpoints.py` (reusan el fixture `client`):

```python
def test_decisions_endpoint_with_indicators(client):
    r = client.get("/api/decisions?limit=5")
    assert r.status_code == 200
    decisions = r.json()
    assert len(decisions) == 1
    d = decisions[0]
    assert d["action"] == "BUY"
    assert d["reason"] == "cruce alcista"
    assert d["rsi"] == 41.0
    assert d["ema_fast"] == 30.5
    assert d["ema_slow"] == 29.0


def test_fills_endpoint(client):
    r = client.get("/api/fills?limit=10")
    assert r.status_code == 200
    fills = r.json()
    assert len(fills) == 1
    assert fills[0]["side"] == "BUY"
    assert fills[0]["price"] == 100.0
    assert fills[0]["quantity"] == 0.01
```

- [ ] **Step 2: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_endpoints.py -q`
Expected: FAIL — los dos endpoints nuevos devuelven `404 Not Found` (`assert 404 == 200`).

- [ ] **Step 3: Implementar** — en `api/app.py`:

(a) extender el import de modelos:

```python
from api.models import EquityPoint, PositionOut, StatusResponse
```

por:

```python
from api.models import DecisionOut, EquityPoint, FillOut, PositionOut, StatusResponse
```

(b) agregar las dos rutas dentro de `create_app`, **antes** de `return app`:

```python
    @app.get("/api/decisions", response_model=list[DecisionOut])
    def decisions(limit: int = 20, store: Store = Depends(get_store)) -> list[DecisionOut]:
        return [DecisionOut(**row) for row in store.recent_decisions(limit)]

    @app.get("/api/fills", response_model=list[FillOut])
    def fills(limit: int = 50, store: Store = Depends(get_store)) -> list[FillOut]:
        return [FillOut(**row) for row in store.recent_fills(limit)]
```

- [ ] **Step 4: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_endpoints.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add api/app.py tests/test_api_endpoints.py
git commit -m "feat: add decisions and fills endpoints" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: CORS + cableado final de la app (TDD)

**Files:**
- Modify: `api/app.py`
- Test: `tests/test_api_endpoints.py` (agregar test)

**Interfaces:**
- Produces: `CORSMiddleware` habilitado para los orígenes del frontend dev (`http://localhost:5173`, `http://127.0.0.1:5173`), override por env `AMERICO_CORS_ORIGINS` (lista separada por comas). Métodos `GET`, headers `*`.

- [ ] **Step 1: Agregar el test que falla** — añadir a `tests/test_api_endpoints.py`:

```python
def test_cors_allows_dev_origin(client):
    r = client.get("/api/status", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
```

- [ ] **Step 2: Run para verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_endpoints.py::test_cors_allows_dev_origin -q`
Expected: FAIL con `KeyError: 'access-control-allow-origin'` (no hay middleware CORS todavía).

- [ ] **Step 3: Implementar** — en `api/app.py`:

(a) agregar imports al inicio (debajo de `from __future__ import annotations`):

```python
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
```

(reemplazando la línea `from fastapi import Depends, FastAPI` existente; `import os` queda arriba de los imports de terceros).

(b) agregar la función módulo-nivel (encima de `create_app`):

```python
def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "AMERICO_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]
```

(c) dentro de `create_app`, **inmediatamente después** de `app = FastAPI(...)`:

```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
```

- [ ] **Step 4: Run y verificar verde**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: PASS (toda la suite verde, incluido el test de CORS).

- [ ] **Step 5: Verificación manual del servidor (opcional)**

Run: `.venv/Scripts/python.exe -m uvicorn api.app:app --reload`
Expected: Uvicorn levanta en `http://127.0.0.1:8000`; `http://127.0.0.1:8000/api/health` devuelve `{"status":"ok"}` y `http://127.0.0.1:8000/docs` muestra los 6 endpoints. Cortar con Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add api/app.py tests/test_api_endpoints.py
git commit -m "feat: enable CORS for the dev frontend" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Scaffold del frontend (Vite + TS + Tailwind + shadcn primitives)

**Files:**
- Create: `web/` (scaffold Vite), `web/vite.config.ts`, `web/tailwind.config.js`, `web/postcss.config.js`, `web/src/index.css`, `web/src/lib/utils.ts`, `web/src/components/ui/{button,card,badge,table,tabs}.tsx`
- Modify: `web/tsconfig.app.json` (alias `@`)

**Interfaces:**
- Produces: proyecto Vite compilable (`npm run build`) con Tailwind activo, alias `@ -> ./src`, y las primitivas shadcn `Button`, `Card`/`CardHeader`/`CardTitle`/`CardContent`, `Badge`, `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableHead`/`TableCell`, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`, más `cn()`.

> Todos los comandos de esta task y de las 8–9 se ejecutan **dentro de `web/`**.

- [ ] **Step 1: Scaffold Vite** (desde la raíz del repo):

```bash
npm create vite@latest web -- --template react-ts
```

- [ ] **Step 2: Instalar dependencias** (desde `web/`):

```bash
npm install
npm install recharts lucide-react class-variance-authority clsx tailwind-merge @radix-ui/react-tabs
npm install -D tailwindcss@3 postcss autoprefixer
```

- [ ] **Step 3: `web/tailwind.config.js`:**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 4: `web/postcss.config.js`:**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: `web/src/index.css`** (reemplazar todo el contenido):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
}

body {
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
}
```

- [ ] **Step 6: `web/vite.config.ts`** (reemplazar todo el contenido):

```ts
import { fileURLToPath, URL } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
```

- [ ] **Step 7: Alias en TS** — en `web/tsconfig.app.json`, dentro de `compilerOptions`, agregar:

```json
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
```

- [ ] **Step 8: `web/src/lib/utils.ts`:**

```ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 9: `web/src/components/ui/button.tsx`:**

```tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-zinc-900 text-zinc-50 hover:bg-zinc-800',
        destructive: 'bg-red-600 text-zinc-50 hover:bg-red-500',
        outline: 'border border-zinc-200 bg-white hover:bg-zinc-100',
        ghost: 'hover:bg-zinc-100',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
```

- [ ] **Step 10: `web/src/components/ui/card.tsx`:**

```tsx
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('rounded-xl border border-zinc-200 bg-white shadow-sm', className)} {...props} />
  ),
)
Card.displayName = 'Card'

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-4', className)} {...props} />
  ),
)
CardHeader.displayName = 'CardHeader'

export const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-sm font-medium text-zinc-500', className)} {...props} />
  ),
)
CardTitle.displayName = 'CardTitle'

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-4 pt-0', className)} {...props} />
  ),
)
CardContent.displayName = 'CardContent'
```

- [ ] **Step 11: `web/src/components/ui/badge.tsx`:**

```tsx
import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-zinc-100 text-zinc-700',
        success: 'border-transparent bg-emerald-100 text-emerald-700',
        danger: 'border-transparent bg-red-100 text-red-700',
        warning: 'border-transparent bg-amber-100 text-amber-700',
        outline: 'border-zinc-200 text-zinc-600',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
```

- [ ] **Step 12: `web/src/components/ui/table.tsx`:**

```tsx
import * as React from 'react'
import { cn } from '@/lib/utils'

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-auto">
      <table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} />
    </div>
  ),
)
Table.displayName = 'Table'

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <thead ref={ref} className={cn('[&_tr]:border-b', className)} {...props} />,
)
TableHeader.displayName = 'TableHeader'

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props} />,
)
TableBody.displayName = 'TableBody'

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr ref={ref} className={cn('border-b border-zinc-100 transition-colors hover:bg-zinc-50', className)} {...props} />
  ),
)
TableRow.displayName = 'TableRow'

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th ref={ref} className={cn('h-10 px-3 text-left align-middle text-xs font-medium text-zinc-500', className)} {...props} />
  ),
)
TableHead.displayName = 'TableHead'

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn('p-3 align-middle', className)} {...props} />
  ),
)
TableCell.displayName = 'TableCell'
```

- [ ] **Step 13: `web/src/components/ui/tabs.tsx`:**

```tsx
import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'
import { cn } from '@/lib/utils'

export const Tabs = TabsPrimitive.Root

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn('inline-flex h-9 items-center justify-center rounded-lg bg-zinc-100 p-1 text-zinc-500', className)}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all data-[state=active]:bg-white data-[state=active]:text-zinc-900 data-[state=active]:shadow',
      className,
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

export const TabsContent = TabsPrimitive.Content
```

- [ ] **Step 14: Verificar el build**

Run (desde `web/`): `npm run build`
Expected: `tsc -b && vite build` termina sin errores y genera `web/dist/`. (El `App.tsx` por defecto del scaffold sigue presente; se reemplaza en la Task 9.)

- [ ] **Step 15: Commit** (desde la raíz):

```bash
git add web
git commit -m "feat: scaffold web panel (vite, tailwind, shadcn primitives)" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> Nota: revisá que `web/.gitignore` (creado por Vite) excluya `node_modules` y `dist`.

---

### Task 8: Cliente de API + tipos + utilidades puras (vitest TDD) + hook `usePolling`

**Files:**
- Create: `web/src/lib/types.ts`, `web/src/lib/api.ts`, `web/src/lib/format.ts`, `web/src/lib/format.test.ts`, `web/src/lib/use-polling.ts`, `web/vitest.config.ts`
- Modify: `web/package.json` (script `test`)

**Interfaces:**
- Produces:
  - `types.ts`: `Status`, `EquityPoint`, `Position`, `Decision`, `Fill`.
  - `api.ts`: `api.getStatus()`, `getEquity(limit?)`, `getPositions()`, `getDecisions(limit?)`, `getFills(limit?)` (fetch tipado; base `VITE_API_BASE` o `http://localhost:8000`).
  - `format.ts` (puro, testeado): `formatUsd(n)`, `formatPct(n)`, `pnlColor(n)`, `actionLabel(a)`, `pnlAbsolute(series)`, `winRate(series)`.
  - `use-polling.ts`: `usePolling<T>(fn, intervalMs) -> { data, error, loading }`.

- [ ] **Step 1: Instalar vitest** (desde `web/`):

```bash
npm install -D vitest
```

- [ ] **Step 2: `web/vitest.config.ts`:**

```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
```

- [ ] **Step 3: Script de test** — en `web/package.json`, dentro de `"scripts"`, agregar:

```json
    "test": "vitest run"
```

- [ ] **Step 4: `web/src/lib/types.ts`:**

```ts
export interface Status {
  exchange: string
  timeframe: string
  broker_kind: string
  symbols: string[]
  equity: number
  cash: number
}

export interface EquityPoint {
  ts: string
  equity: number
  cash: number
}

export interface Position {
  symbol: string
  quantity: number
  entry_price: number
  stop_loss: number
  take_profit: number
}

export interface Decision {
  ts: string
  symbol: string
  action: string
  reason: string
  ema_fast: number
  ema_slow: number
  rsi: number
}

export interface Fill {
  ts: string
  symbol: string
  side: string
  quantity: number
  price: number
  fee: number
}
```

- [ ] **Step 5: Escribir el test que falla** — `web/src/lib/format.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import {
  actionLabel,
  formatPct,
  formatUsd,
  pnlAbsolute,
  pnlColor,
  winRate,
} from './format'

describe('formatUsd', () => {
  it('formatea con símbolo y 2 decimales', () => {
    expect(formatUsd(10000)).toBe('$10,000.00')
    expect(formatUsd(1234.5)).toBe('$1,234.50')
  })
})

describe('formatPct', () => {
  it('agrega signo y porcentaje', () => {
    expect(formatPct(0.0123)).toBe('+1.23%')
    expect(formatPct(-0.05)).toBe('-5.00%')
    expect(formatPct(0)).toBe('0.00%')
  })
})

describe('pnlColor', () => {
  it('verde / rojo / neutro según el signo', () => {
    expect(pnlColor(1)).toBe('text-emerald-600')
    expect(pnlColor(-1)).toBe('text-red-600')
    expect(pnlColor(0)).toBe('text-zinc-500')
  })
})

describe('actionLabel', () => {
  it('traduce las acciones al español', () => {
    expect(actionLabel('BUY')).toBe('COMPRAR')
    expect(actionLabel('SELL')).toBe('VENDER')
    expect(actionLabel('HOLD')).toBe('MANTENER')
    expect(actionLabel('OTRA')).toBe('OTRA')
  })
})

describe('pnlAbsolute', () => {
  it('último menos primero; 0 con menos de 2 puntos', () => {
    expect(pnlAbsolute([])).toBe(0)
    expect(pnlAbsolute([{ ts: 't', equity: 100, cash: 0 }])).toBe(0)
    expect(
      pnlAbsolute([
        { ts: 't1', equity: 100, cash: 0 },
        { ts: 't2', equity: 130, cash: 0 },
      ]),
    ).toBe(30)
  })
})

describe('winRate', () => {
  it('fracción de variaciones positivas de equity', () => {
    expect(winRate([])).toBe(0)
    expect(
      winRate([
        { ts: 't1', equity: 100, cash: 0 },
        { ts: 't2', equity: 110, cash: 0 },
        { ts: 't3', equity: 105, cash: 0 },
        { ts: 't4', equity: 120, cash: 0 },
      ]),
    ).toBeCloseTo(2 / 3)
  })
})
```

- [ ] **Step 6: Run para verificar que falla**

Run (desde `web/`): `npx vitest run`
Expected: FAIL — no existe `./format` (error de resolución del import).

- [ ] **Step 7: Implementar `web/src/lib/format.ts`:**

```ts
import type { EquityPoint } from './types'

export function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatPct(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(2)}%`
}

export function pnlColor(value: number): string {
  if (value > 0) return 'text-emerald-600'
  if (value < 0) return 'text-red-600'
  return 'text-zinc-500'
}

export function actionLabel(action: string): string {
  switch (action) {
    case 'BUY':
      return 'COMPRAR'
    case 'SELL':
      return 'VENDER'
    case 'HOLD':
      return 'MANTENER'
    default:
      return action
  }
}

export function pnlAbsolute(series: EquityPoint[]): number {
  if (series.length < 2) return 0
  return series[series.length - 1].equity - series[0].equity
}

export function winRate(series: EquityPoint[]): number {
  if (series.length < 2) return 0
  let wins = 0
  let total = 0
  for (let i = 1; i < series.length; i++) {
    total += 1
    if (series[i].equity > series[i - 1].equity) wins += 1
  }
  return total === 0 ? 0 : wins / total
}
```

- [ ] **Step 8: Run y verificar verde**

Run (desde `web/`): `npx vitest run`
Expected: PASS (6 passed).

- [ ] **Step 9: Implementar `web/src/lib/api.ts`:**

```ts
import type { Decision, EquityPoint, Fill, Position, Status } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status} en ${path}`)
  return (await res.json()) as T
}

export const api = {
  getStatus: () => getJson<Status>('/api/status'),
  getEquity: (limit = 200) => getJson<EquityPoint[]>(`/api/equity?limit=${limit}`),
  getPositions: () => getJson<Position[]>('/api/positions'),
  getDecisions: (limit = 20) => getJson<Decision[]>(`/api/decisions?limit=${limit}`),
  getFills: (limit = 50) => getJson<Fill[]>(`/api/fills?limit=${limit}`),
}
```

- [ ] **Step 10: Implementar `web/src/lib/use-polling.ts`:**

```ts
import { useEffect, useRef, useState } from 'react'

export interface PollingState<T> {
  data: T | null
  error: Error | null
  loading: boolean
}

export function usePolling<T>(fn: () => Promise<T>, intervalMs: number): PollingState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    let active = true
    const tick = async () => {
      try {
        const result = await fnRef.current()
        if (active) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (active) setError(err as Error)
      } finally {
        if (active) setLoading(false)
      }
    }
    tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      active = false
      clearInterval(id)
    }
  }, [intervalMs])

  return { data, error, loading }
}
```

- [ ] **Step 11: Verificar que el proyecto sigue compilando**

Run (desde `web/`): `npm run build`
Expected: build sin errores de tipos (los nuevos módulos compilan; `App.tsx` del scaffold todavía no los usa).

- [ ] **Step 12: Commit** (desde la raíz):

```bash
git add web
git commit -m "feat: add typed api client, formatters and usePolling hook" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Componentes del panel cableados al cliente

**Files:**
- Create: `web/src/components/{TopBar,KpiRow,EquityChart,DecisionCard,PositionsTable,HistoryTable,ActivityLog}.tsx`
- Modify: `web/src/App.tsx`, `web/.env` (opcional)

**Interfaces:**
- Consumes: `@/lib/api`, `@/lib/use-polling`, `@/lib/format`, `@/lib/types`, primitivas `@/components/ui/*`, Recharts, lucide-react.
- Produces: el panel completo (TopBar + 4 KPIs + chart + DecisionCard + tabla de posiciones + historial + log de actividad) renderizado en `App.tsx` con polling cada 5 s.

- [ ] **Step 1: `web/src/components/TopBar.tsx`:**

```tsx
import { Settings } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Status } from '@/lib/types'

const TABS = ['Panel', 'Backtest', 'Historial', 'Config']

export function TopBar({ status }: { status: Status | null }) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-emerald-500" />
          <span className="text-lg font-semibold text-zinc-900">Américo</span>
        </div>
        <nav className="flex items-center gap-1">
          {TABS.map((t, i) => (
            <button
              key={t}
              className={
                i === 0
                  ? 'rounded-md bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900'
                  : 'rounded-md px-3 py-1.5 text-sm text-zinc-500 hover:text-zinc-900'
              }
            >
              {t}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="success">Operando</Badge>
        {status?.broker_kind === 'paper' && <Badge variant="warning">PAPER</Badge>}
        <span className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm text-zinc-600 tabular-nums">
          {status ? `${status.exchange.toUpperCase()} · ${status.timeframe}` : '—'}
        </span>
        <Button variant="destructive" size="sm">
          Detener
        </Button>
        <Button variant="ghost" size="icon" aria-label="Configuración">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: `web/src/components/KpiRow.tsx`:**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatPct, formatUsd, pnlAbsolute, pnlColor, winRate } from '@/lib/format'
import type { EquityPoint, Status } from '@/lib/types'

function todaySeries(series: EquityPoint[]): EquityPoint[] {
  const today = new Date().toISOString().slice(0, 10)
  const filtered = series.filter((p) => p.ts.slice(0, 10) === today)
  return filtered.length >= 2 ? filtered : series
}

export function KpiRow({ status, series }: { status: Status | null; series: EquityPoint[] }) {
  const equity = status?.equity ?? (series.length ? series[series.length - 1].equity : 0)
  const pnlToday = pnlAbsolute(todaySeries(series))
  const pnlTotal = pnlAbsolute(series)
  const base = series.length ? series[0].equity : 0
  const pnlTotalPct = base > 0 ? pnlTotal / base : 0
  const wr = winRate(series)

  const cards = [
    { title: 'Equity', value: formatUsd(equity), delta: null as string | null, color: 'text-zinc-900' },
    { title: 'P&L de hoy', value: formatUsd(pnlToday), delta: null, color: pnlColor(pnlToday) },
    { title: 'P&L total', value: formatUsd(pnlTotal), delta: formatPct(pnlTotalPct), color: pnlColor(pnlTotal) },
    { title: 'Win rate', value: formatPct(wr).replace('+', ''), delta: null, color: 'text-zinc-900' },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.title}>
          <CardHeader className="pb-2">
            <CardTitle>{c.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`font-mono text-2xl font-semibold tabular-nums ${c.color}`}>{c.value}</div>
            {c.delta && <div className={`mt-1 text-xs font-medium ${c.color}`}>{c.delta}</div>}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

> Simplificación (documentada): "P&L de hoy" usa los snapshots de equity de la fecha actual (o toda la serie si hay menos de 2 puntos hoy); "Win rate" es la fracción de variaciones positivas de equity en la serie. Ambas se afinarán cuando se persista el P&L por trade.

- [ ] **Step 3: `web/src/components/EquityChart.tsx`:**

```tsx
import { useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatUsd } from '@/lib/format'
import type { EquityPoint } from '@/lib/types'

export function EquityChart({ series }: { series: EquityPoint[] }) {
  const [view, setView] = useState('equity')
  const data = series.map((p) => ({ t: p.ts.slice(11, 16), equity: p.equity, cash: p.cash }))

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-zinc-900">Evolución del equity</CardTitle>
        <Tabs value={view} onValueChange={setView}>
          <TabsList>
            <TabsTrigger value="equity">Equity</TabsTrigger>
            <TabsTrigger value="price">Precio</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        {view === 'price' && (
          <p className="mb-2 text-xs text-zinc-400">Vista de precio próximamente — mostrando equity.</p>
        )}
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
              <XAxis dataKey="t" tick={{ fontSize: 11, fill: '#a1a1aa' }} />
              <YAxis tick={{ fontSize: 11, fill: '#a1a1aa' }} width={70} tickFormatter={(v) => formatUsd(Number(v))} />
              <Tooltip formatter={(v) => formatUsd(Number(v))} />
              <Area type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} fill="url(#eq)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: `web/src/components/DecisionCard.tsx`:**

```tsx
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actionLabel } from '@/lib/format'
import type { Decision } from '@/lib/types'

function actionVariant(action: string): 'success' | 'danger' | 'default' {
  if (action === 'BUY') return 'success'
  if (action === 'SELL') return 'danger'
  return 'default'
}

export function DecisionCard({ decision }: { decision: Decision | null }) {
  const [ia, setIa] = useState(false)
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-zinc-900">Decisión de Américo</CardTitle>
        <button
          onClick={() => setIa((v) => !v)}
          className={
            ia
              ? 'rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700'
              : 'rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-500'
          }
        >
          IA {ia ? 'ON' : 'OFF'}
        </button>
      </CardHeader>
      <CardContent>
        {decision ? (
          <div className="space-y-3">
            <Badge variant={actionVariant(decision.action)} className="text-sm">
              {actionLabel(decision.action)}
            </Badge>
            <p className="text-sm text-zinc-600">{decision.reason}</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">RSI {decision.rsi.toFixed(1)}</Badge>
              <Badge variant="outline">EMA rápida {decision.ema_fast.toFixed(2)}</Badge>
              <Badge variant="outline">EMA lenta {decision.ema_slow.toFixed(2)}</Badge>
            </div>
            <p className="text-xs text-zinc-400 tabular-nums">{decision.ts}</p>
          </div>
        ) : (
          <p className="text-sm text-zinc-400">Sin decisiones todavía.</p>
        )}
      </CardContent>
    </Card>
  )
}
```

> El toggle "IA" es solo visual (`useState` local), sin efecto sobre la lógica por ahora.

- [ ] **Step 5: `web/src/components/PositionsTable.tsx`:**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatUsd, pnlColor } from '@/lib/format'
import type { Position } from '@/lib/types'

export function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">Posiciones abiertas</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Símbolo</TableHead>
              <TableHead>Lado</TableHead>
              <TableHead className="text-right">Entrada</TableHead>
              <TableHead className="text-right">Actual</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead className="text-right">Stop</TableHead>
              <TableHead className="text-right">Take</TableHead>
              <TableHead className="text-right">Valor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-sm text-zinc-400">
                  Sin posiciones abiertas.
                </TableCell>
              </TableRow>
            ) : (
              positions.map((p) => {
                const current = p.entry_price // fallback: sin precio en vivo
                const pnl = (current - p.entry_price) * p.quantity
                const value = current * p.quantity
                return (
                  <TableRow key={p.symbol}>
                    <TableCell className="font-medium">{p.symbol}</TableCell>
                    <TableCell>Largo</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.entry_price)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(current)}</TableCell>
                    <TableCell className={`text-right tabular-nums ${pnlColor(pnl)}`}>{formatUsd(pnl)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.stop_loss)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(p.take_profit)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatUsd(value)}</TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

> Simplificación: "Actual" usa el precio de entrada como fallback (no hay feed de precio en vivo en la API todavía), por lo que el P&L de la posición abierta muestra 0 hasta agregar precio en vivo.

- [ ] **Step 6: `web/src/components/HistoryTable.tsx`:**

```tsx
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatUsd } from '@/lib/format'
import type { Fill } from '@/lib/types'

export function HistoryTable({ fills }: { fills: Fill[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">Historial de operaciones</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Símbolo</TableHead>
              <TableHead>Lado</TableHead>
              <TableHead className="text-right">Cantidad</TableHead>
              <TableHead className="text-right">Precio</TableHead>
              <TableHead className="text-right">Comisión</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fills.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-sm text-zinc-400">
                  Sin operaciones todavía.
                </TableCell>
              </TableRow>
            ) : (
              fills.map((f, i) => (
                <TableRow key={`${f.ts}-${i}`}>
                  <TableCell className="tabular-nums text-zinc-500">{f.ts.slice(0, 16).replace('T', ' ')}</TableCell>
                  <TableCell className="font-medium">{f.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={f.side === 'BUY' ? 'success' : 'danger'}>
                      {f.side === 'BUY' ? 'COMPRA' : 'VENTA'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{f.quantity.toFixed(6)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatUsd(f.price)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatUsd(f.fee)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 7: `web/src/components/ActivityLog.tsx`:**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actionLabel } from '@/lib/format'
import type { Decision } from '@/lib/types'

function dot(action: string): string {
  if (action === 'BUY') return 'bg-emerald-500'
  if (action === 'SELL') return 'bg-red-500'
  return 'bg-zinc-300'
}

export function ActivityLog({ decisions }: { decisions: Decision[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">Actividad reciente</CardTitle>
      </CardHeader>
      <CardContent>
        {decisions.length === 0 ? (
          <p className="text-sm text-zinc-400">Sin actividad todavía.</p>
        ) : (
          <ul className="space-y-3">
            {decisions.map((d, i) => (
              <li key={`${d.ts}-${i}`} className="flex items-start gap-3">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot(d.action)}`} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-zinc-900">{actionLabel(d.action)}</span>
                    <span className="text-xs text-zinc-400">{d.symbol}</span>
                  </div>
                  <p className="truncate text-xs text-zinc-500">{d.reason}</p>
                  <p className="text-xs text-zinc-300 tabular-nums">{d.ts.slice(0, 16).replace('T', ' ')}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 8: `web/src/App.tsx`** (reemplazar todo el contenido):

```tsx
import { useCallback } from 'react'
import { ActivityLog } from '@/components/ActivityLog'
import { DecisionCard } from '@/components/DecisionCard'
import { EquityChart } from '@/components/EquityChart'
import { HistoryTable } from '@/components/HistoryTable'
import { KpiRow } from '@/components/KpiRow'
import { PositionsTable } from '@/components/PositionsTable'
import { TopBar } from '@/components/TopBar'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const INTERVAL = 5000

export default function App() {
  const status = usePolling(useCallback(() => api.getStatus(), []), INTERVAL)
  const equity = usePolling(useCallback(() => api.getEquity(200), []), INTERVAL)
  const positions = usePolling(useCallback(() => api.getPositions(), []), INTERVAL)
  const decisions = usePolling(useCallback(() => api.getDecisions(20), []), INTERVAL)
  const fills = usePolling(useCallback(() => api.getFills(50), []), INTERVAL)

  const series = equity.data ?? []
  const decisionList = decisions.data ?? []

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <TopBar status={status.data} />
      <main className="mx-auto max-w-7xl space-y-4 p-6">
        {status.error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            No se pudo conectar con la API. ¿Está corriendo uvicorn en el puerto 8000?
          </div>
        )}
        <KpiRow status={status.data} series={series} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <EquityChart series={series} />
          </div>
          <DecisionCard decision={decisionList[0] ?? null} />
        </div>
        <PositionsTable positions={positions.data ?? []} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HistoryTable fills={fills.data ?? []} />
          <ActivityLog decisions={decisionList} />
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 9: `web/.env`** (opcional, para fijar la URL de la API):

```
VITE_API_BASE=http://localhost:8000
```

- [ ] **Step 10: Limpiar restos del scaffold** — borrar `web/src/App.css` si quedó importado; asegurarse de que `web/src/main.tsx` importe `./index.css` (no `App.css`). Contenido esperado de `web/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 11: Verificar build + dev contra la API**

Run (desde `web/`): `npm run build`
Expected: compila sin errores de tipos.

Luego, con el backend corriendo en otra terminal (`.venv/Scripts/python.exe -m uvicorn api.app:app --reload`):
Run (desde `web/`): `npm run dev`
Expected: Vite sirve en `http://localhost:5173`; el panel carga, hace polling cada 5 s y muestra los datos de la API (o el banner rojo si la API está caída). Sin errores CORS en la consola del navegador.

- [ ] **Step 12: Commit** (desde la raíz):

```bash
git add web
git commit -m "feat: wire panel components to the API client" -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Verificación end-to-end manual (bot → uvicorn → vite → estado real)

**Files:** ninguno (solo verificación).

**Interfaces:** ninguna nueva.

- [ ] **Step 1: Generar estado real con el bot** (desde la raíz, `broker.kind: paper` en `config.yaml`):

```bash
.venv/Scripts/python.exe -m bot run BTC/USDT --timeframe 1h
.venv/Scripts/python.exe -m bot status
```

Expected: el bot baja datos reales, decide sobre la vela cerrada, persiste decisión/equity (y un fill + posición si la señal fue BUY/SELL) en `americo.sqlite`. `status` muestra equity, caja, posiciones y últimas decisiones. (Si OKX está geo-restringido, usar `--exchange kraken`.)

- [ ] **Step 2: Levantar la API** (terminal 1, desde la raíz):

```bash
.venv/Scripts/python.exe -m uvicorn api.app:app --reload
```

Expected: Uvicorn en `http://127.0.0.1:8000`; `GET /api/status`, `/api/equity`, `/api/decisions`, `/api/positions`, `/api/fills` devuelven el estado real recién generado.

- [ ] **Step 3: Levantar el panel** (terminal 2, desde `web/`):

```bash
npm run dev
```

Expected: en `http://localhost:5173` el panel muestra el estado real: el pill "Operando" + "PAPER", el selector `OKX · 1h`, los 4 KPIs (Equity con el valor real, P&L y win rate derivados), el chart de equity, la tarjeta "Decisión de Américo" con la última acción/indicadores, y las tablas de posiciones / historial / actividad pobladas. Al volver a correr `python -m bot run ...` y esperar ~5 s, el panel se actualiza solo por el polling.

- [ ] **Step 4: Checklist visual final**
  - [ ] Tema claro zinc, tarjetas blancas con bordes sutiles, acento emerald.
  - [ ] Números monoespaciados (`tabular-nums`); P&L en verde/rojo según signo.
  - [ ] Sin errores en la consola del navegador (incl. CORS).
  - [ ] El banner rojo aparece si se corta la API y desaparece al reanudarla.

---

## Resultado de la Fase 3

Al completar las 10 tasks, AMÉRICO deja de ser solo CLI: el mismo estado en SQLite queda **expuesto por una API FastAPI de solo lectura** (6 endpoints JSON con modelos Pydantic y CORS, totalmente cubiertos por tests con `TestClient` sin red) y **visualizado en vivo por un panel web** (Vite + React + TS + Tailwind + shadcn/ui + Recharts) que hace polling cada 5 segundos y reproduce el diseño claro de Pencil: top bar con pills de estado, 4 KPIs, chart de equity, la tarjeta "Decisión de Américo", y las tablas de posiciones, historial y actividad. Las utilidades puras del frontend se validan con vitest. Quedan documentadas como simplificaciones deliberadas: el estado "Operando/PAPER" se deriva de la config (no hay flag de corrida persistido), el "precio actual" de las posiciones usa el precio de entrada como fallback (sin feed en vivo), y "P&L de hoy" / "Win rate" se derivan de la serie de equity hasta que se persista el P&L por trade. La base queda lista para iterar: precio en vivo, P&L por trade exacto, control real de start/stop desde el botón "Detener", y autenticación.
