# Fase 1 — Capa de datos multi-cuenta · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescribir la capa `Store` con SQLAlchemy Core, agregando una columna `account` a todos los datos y una tabla `accounts`, corriendo en SQLite por defecto y en Postgres con solo setear `DATABASE_URL`, sin romper la cuenta única actual (`account="default"`).

**Architecture:** Un módulo de esquema (SQLAlchemy Core `MetaData` con las tablas), una fábrica de `Engine` que elige SQLite o Postgres según `DATABASE_URL`, y un `Store` que recibe `account` en cada método. Los consumidores actuales (engine del bot, CLI, API) pasan `account="default"` para mantener el comportamiento previo.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (Core), psycopg 3 (driver Postgres), pytest, FastAPI.

## Global Constraints

- DB agnóstica: **SQLite por defecto** (`sqlite:///<db_path>`), **Postgres** si está la env `DATABASE_URL`. Mismo SQL para ambos (SQLAlchemy Core).
- SQLite multi-hilo: `connect_args={"check_same_thread": False}` (la flota futura corre hilos en un proceso).
- Compatibilidad: todos los métodos de `Store` reciben `account: str`; los llamadores actuales pasan `"default"`. Los datos viejos se migran a `account="default"`.
- Estilo existente: `from __future__ import annotations`, tipado, dataclasses (`bot/broker/models.py` define `Fill`, `Position`, `Side`).
- TDD. Tests con `.venv/Scripts/python.exe -m pytest -q`. Commits frecuentes.
- No romper los 92 tests existentes (algunos llaman al `Store` viejo — se actualizan en las tareas que tocan sus llamadores).

---

### Task 1: Dependencias + fábrica de Engine

**Files:**
- Modify: `requirements.txt`
- Create: `bot/store/engine.py`
- Test: `tests/test_store_engine.py`

**Interfaces:**
- Produces: `make_engine(target: str = ":memory:") -> sqlalchemy.Engine`. Si la env `DATABASE_URL` está seteada, la usa. Si `target` contiene `"://"`, se usa tal cual como URL. Si es `":memory:"` → `sqlite:///:memory:` con pool compartido. Si no, `sqlite:///{target}`. Para SQLite agrega `connect_args={"check_same_thread": False}`.

- [ ] **Step 1: Agregar dependencias**

En `requirements.txt`, agregar al final:
```
SQLAlchemy>=2.0
psycopg[binary]>=3.1
```
Instalar: `.venv/Scripts/python.exe -m pip install "SQLAlchemy>=2.0" "psycopg[binary]>=3.1"`

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/test_store_engine.py
from __future__ import annotations

import os

from sqlalchemy import Engine, text

from bot.store.engine import make_engine, normalize_url


def test_memory_engine_is_sqlite():
    eng = make_engine(":memory:")
    assert isinstance(eng, Engine)
    assert eng.dialect.name == "sqlite"
    with eng.connect() as c:
        assert c.execute(text("select 1")).scalar() == 1


def test_path_becomes_sqlite_url(tmp_path):
    eng = make_engine(str(tmp_path / "x.sqlite"))
    assert eng.dialect.name == "sqlite"


def test_database_url_env_overrides(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    eng = make_engine("ignored.sqlite")
    assert eng.dialect.name == "sqlite"


def test_postgres_url_normalized_to_psycopg3():
    # Coolify entrega postgres://... — debe forzar el driver psycopg 3.
    assert normalize_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"
```

- [ ] **Step 3: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_engine.py -q`
Expected: FAIL (`ModuleNotFoundError: bot.store.engine`).

- [ ] **Step 4: Implementar la fábrica**

```python
# bot/store/engine.py
from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool


def normalize_url(url: str) -> str:
    """Fuerza el driver psycopg 3 en URLs de Postgres (Coolify da postgres://...)."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def make_engine(target: str = ":memory:") -> Engine:
    """Devuelve un Engine de SQLAlchemy.

    - Si DATABASE_URL está seteada, se usa esa URL (Postgres en Coolify).
    - Si `target` ya es una URL (contiene '://'), se usa tal cual.
    - ":memory:" -> SQLite en memoria con pool estático (compartible entre hilos).
    - Cualquier otra cosa se interpreta como path de archivo SQLite.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return create_engine(normalize_url(url), future=True)
    if "://" in target:
        return create_engine(normalize_url(target), future=True)
    if target == ":memory:":
        return create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        f"sqlite:///{target}",
        future=True,
        connect_args={"check_same_thread": False},
    )
```

- [ ] **Step 5: Verificar verde y commitear**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_engine.py -q` → PASS
```bash
git add requirements.txt bot/store/engine.py tests/test_store_engine.py
git commit -m "feat(store): fabrica de Engine SQLAlchemy (SQLite default, Postgres via DATABASE_URL)"
```

---

### Task 2: Esquema con columna `account` + tabla `accounts`

**Files:**
- Create: `bot/store/schema.py`
- Test: `tests/test_store_schema.py`

**Interfaces:**
- Produces: `metadata` (`sqlalchemy.MetaData`) y las `Table`: `decisions`, `fills`, `positions`, `equity`, `accounts`. `create_all(engine)` crea todo. `positions` tiene PK compuesta `(account, symbol)`. Columnas exactas detalladas abajo.

- [ ] **Step 1: Test que falla**

```python
# tests/test_store_schema.py
from __future__ import annotations

from sqlalchemy import inspect

from bot.store.engine import make_engine
from bot.store.schema import metadata


def test_create_all_makes_tables():
    eng = make_engine(":memory:")
    metadata.create_all(eng)
    names = set(inspect(eng).get_table_names())
    assert {"decisions", "fills", "positions", "equity", "accounts"} <= names


def test_account_columns_present():
    eng = make_engine(":memory:")
    metadata.create_all(eng)
    insp = inspect(eng)
    for table in ("decisions", "fills", "positions", "equity"):
        cols = {c["name"] for c in insp.get_columns(table)}
        assert "account" in cols, f"falta account en {table}"
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_schema.py -q`
Expected: FAIL (`ModuleNotFoundError: bot.store.schema`).

- [ ] **Step 3: Implementar el esquema**

```python
# bot/store/schema.py
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
)

metadata = MetaData()

decisions = Table(
    "decisions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("ema_fast", Float),
    Column("ema_slow", Float),
    Column("rsi", Float),
    Column("ai_action", Text),
    Column("ai_confidence", Float),
    Column("ai_rationale", Text),
)

fills = Table(
    "fills", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("quantity", Float, nullable=False),
    Column("price", Float, nullable=False),
    Column("fee", Float, nullable=False),
)

positions = Table(
    "positions", metadata,
    Column("account", Text, primary_key=True),
    Column("symbol", Text, primary_key=True),
    Column("quantity", Float, nullable=False),
    Column("entry_price", Float, nullable=False),
    Column("stop_loss", Float, nullable=False),
    Column("take_profit", Float, nullable=False),
    Column("opened_at", Text, nullable=False),
)

equity = Table(
    "equity", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("equity", Float, nullable=False),
    Column("cash", Float, nullable=False),
)

accounts = Table(
    "accounts", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("strategy", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("timeframe", Text, nullable=False),
    Column("interval_seconds", Integer, nullable=False),
    Column("starting_cash", Float, nullable=False),
    Column("ai_enabled", Boolean, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("params", JSON, nullable=False),
)
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_schema.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add bot/store/schema.py tests/test_store_schema.py
git commit -m "feat(store): esquema SQLAlchemy con columna account y tabla accounts"
```

---

### Task 3: Store account-aware — decisiones y equity

**Files:**
- Modify: `bot/store/db.py` (reescritura completa de `Store` sobre SQLAlchemy)
- Test: `tests/test_store_decisions_equity.py`

**Interfaces:**
- Consumes: `make_engine` (Task 1), `metadata` + tablas (Task 2).
- Produces: `Store(target: str = ":memory:")`. Métodos de esta tarea:
  - `record_decision(account, ts, symbol, action, reason, ema_fast, ema_slow, rsi, ai_action=None, ai_confidence=None, ai_rationale=None) -> None`
  - `recent_decisions(account, limit=10) -> list[dict]` (orden id DESC; dicts con las mismas claves que las columnas, sin `id`/`account`)
  - `record_equity(account, ts, equity, cash) -> None`
  - `latest_equity(account) -> tuple[float, float] | None`
  - `equity_series(account, limit=200) -> list[dict]` (cronológico; claves `ts,equity,cash`)
  - `close() -> None`

- [ ] **Step 1: Test que falla**

```python
# tests/test_store_decisions_equity.py
from __future__ import annotations

from bot.store.db import Store


def test_decisions_isolated_by_account():
    s = Store(":memory:")
    s.record_decision("a", "2026-01-01T00:00:00+00:00", "BTC/USDT", "BUY", "r", 1.0, 2.0, 30.0)
    s.record_decision("b", "2026-01-01T00:00:01+00:00", "ETH/USDT", "SELL", "r2", 3.0, 4.0, 70.0)
    a = s.recent_decisions("a")
    assert len(a) == 1 and a[0]["symbol"] == "BTC/USDT" and a[0]["action"] == "BUY"
    assert a[0]["ema_fast"] == 1.0 and a[0]["rsi"] == 30.0
    assert len(s.recent_decisions("b")) == 1
    s.close()


def test_equity_latest_and_series_by_account():
    s = Store(":memory:")
    s.record_equity("a", "2026-01-01T00:00:00+00:00", 10000.0, 10000.0)
    s.record_equity("a", "2026-01-01T00:01:00+00:00", 10100.0, 9000.0)
    assert s.latest_equity("a") == (10100.0, 9000.0)
    assert s.latest_equity("b") is None
    series = s.equity_series("a")
    assert [p["equity"] for p in series] == [10000.0, 10100.0]  # cronológico
    s.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_decisions_equity.py -q`
Expected: FAIL (`Store.__init__`/firma vieja; `record_decision` sin `account`).

- [ ] **Step 3: Reescribir `Store` (parte 1)**

Reemplazar **todo** `bot/store/db.py` por:
```python
# bot/store/db.py
from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from bot.broker.models import Fill, Position
from bot.store.engine import make_engine
from bot.store.schema import accounts, decisions, equity, fills, metadata, positions


class Store:
    def __init__(self, target: str = ":memory:") -> None:
        self._engine = make_engine(target)
        metadata.create_all(self._engine)

    # ---- decisiones ----
    def record_decision(
        self, account: str, ts: str, symbol: str, action: str, reason: str,
        ema_fast: float, ema_slow: float, rsi: float,
        ai_action: str | None = None,
        ai_confidence: float | None = None,
        ai_rationale: str | None = None,
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(decisions).values(
                account=account, ts=ts, symbol=symbol, action=action, reason=reason,
                ema_fast=ema_fast, ema_slow=ema_slow, rsi=rsi,
                ai_action=ai_action, ai_confidence=ai_confidence, ai_rationale=ai_rationale,
            ))

    def recent_decisions(self, account: str, limit: int = 10) -> list[dict]:
        cols = [
            decisions.c.ts, decisions.c.symbol, decisions.c.action, decisions.c.reason,
            decisions.c.ema_fast, decisions.c.ema_slow, decisions.c.rsi,
            decisions.c.ai_action, decisions.c.ai_confidence, decisions.c.ai_rationale,
        ]
        stmt = (
            select(*cols)
            .where(decisions.c.account == account)
            .order_by(decisions.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    # ---- equity ----
    def record_equity(self, account: str, ts: str, equity_value: float, cash: float) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(equity).values(
                account=account, ts=ts, equity=equity_value, cash=cash,
            ))

    def latest_equity(self, account: str) -> tuple[float, float] | None:
        stmt = (
            select(equity.c.equity, equity.c.cash)
            .where(equity.c.account == account)
            .order_by(equity.c.id.desc())
            .limit(1)
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        return None if row is None else (row.equity, row.cash)

    def equity_series(self, account: str, limit: int = 200) -> list[dict]:
        stmt = (
            select(equity.c.ts, equity.c.equity, equity.c.cash)
            .where(equity.c.account == account)
            .order_by(equity.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(stmt)]
        return list(reversed(rows))

    def close(self) -> None:
        self._engine.dispose()
```

(Los métodos de fills/positions/accounts se agregan en las Tasks 4 y 5; este archivo va creciendo.)

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_decisions_equity.py -q` → PASS
(Otros tests aún rotos porque llaman a la firma vieja; se arreglan en Tasks 4-7.)

- [ ] **Step 5: Commit**

```bash
git add bot/store/db.py tests/test_store_decisions_equity.py
git commit -m "feat(store): Store SQLAlchemy account-aware (decisiones + equity)"
```

---

### Task 4: Store — fills y posiciones (account-aware)

**Files:**
- Modify: `bot/store/db.py`
- Test: `tests/test_store_fills_positions.py`

**Interfaces:**
- Consumes: `Fill`, `Position`, `Side` de `bot/broker/models.py` (`Fill(symbol, side: Side, quantity, price, fee)`, `Side.BUY/.SELL` con `.value` "BUY"/"SELL"; `Position(symbol, quantity, entry_price, stop_loss, take_profit)`).
- Produces:
  - `record_fill(account, ts, fill: Fill) -> None`
  - `recent_fills(account, limit=50) -> list[dict]` (claves `ts,symbol,side,quantity,price,fee`; orden id DESC)
  - `upsert_position(account, pos: Position, opened_at: str) -> None` (update-or-insert, cross-DB)
  - `remove_position(account, symbol) -> None`
  - `get_positions(account) -> dict[str, Position]`

- [ ] **Step 1: Test que falla**

```python
# tests/test_store_fills_positions.py
from __future__ import annotations

from bot.broker.models import Fill, Position, Side
from bot.store.db import Store


def test_fills_roundtrip_by_account():
    s = Store(":memory:")
    s.record_fill("a", "2026-01-01T00:00:00+00:00", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.1))
    rows = s.recent_fills("a")
    assert rows[0]["side"] == "BUY" and rows[0]["quantity"] == 0.5
    assert s.recent_fills("b") == []
    s.close()


def test_positions_upsert_and_remove():
    s = Store(":memory:")
    s.upsert_position("a", Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0), "2026-01-01T00:00:00+00:00")
    s.upsert_position("a", Position("BTC/USDT", 0.7, 101.0, 99.0, 105.0), "2026-01-01T00:01:00+00:00")
    pos = s.get_positions("a")
    assert set(pos) == {"BTC/USDT"} and pos["BTC/USDT"].quantity == 0.7  # update, no duplicado
    assert s.get_positions("b") == {}
    s.remove_position("a", "BTC/USDT")
    assert s.get_positions("a") == {}
    s.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_fills_positions.py -q`
Expected: FAIL (`record_fill`/`upsert_position` no existen aún en el nuevo Store).

- [ ] **Step 3: Agregar métodos a `Store`**

Agregar estos métodos dentro de la clase `Store` en `bot/store/db.py` (antes de `close`):
```python
    # ---- fills ----
    def record_fill(self, account: str, ts: str, fill: Fill) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(fills).values(
                account=account, ts=ts, symbol=fill.symbol, side=fill.side.value,
                quantity=fill.quantity, price=fill.price, fee=fill.fee,
            ))

    def recent_fills(self, account: str, limit: int = 50) -> list[dict]:
        stmt = (
            select(fills.c.ts, fills.c.symbol, fills.c.side,
                   fills.c.quantity, fills.c.price, fills.c.fee)
            .where(fills.c.account == account)
            .order_by(fills.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    # ---- posiciones (upsert cross-DB: update y si no afecta filas, insert) ----
    def upsert_position(self, account: str, pos: Position, opened_at: str) -> None:
        values = dict(
            quantity=pos.quantity, entry_price=pos.entry_price,
            stop_loss=pos.stop_loss, take_profit=pos.take_profit,
        )
        with self._engine.begin() as conn:
            res = conn.execute(
                update(positions)
                .where(positions.c.account == account, positions.c.symbol == pos.symbol)
                .values(**values)
            )
            if res.rowcount == 0:
                conn.execute(insert(positions).values(
                    account=account, symbol=pos.symbol, opened_at=opened_at, **values,
                ))

    def remove_position(self, account: str, symbol: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                delete(positions)
                .where(positions.c.account == account, positions.c.symbol == symbol)
            )

    def get_positions(self, account: str) -> dict[str, Position]:
        stmt = select(
            positions.c.symbol, positions.c.quantity, positions.c.entry_price,
            positions.c.stop_loss, positions.c.take_profit,
        ).where(positions.c.account == account)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return {
            r.symbol: Position(r.symbol, r.quantity, r.entry_price, r.stop_loss, r.take_profit)
            for r in rows
        }
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_fills_positions.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add bot/store/db.py tests/test_store_fills_positions.py
git commit -m "feat(store): fills y posiciones account-aware (upsert cross-DB)"
```

---

### Task 5: CRUD de la tabla `accounts`

**Files:**
- Modify: `bot/store/db.py`
- Test: `tests/test_store_accounts.py`

**Interfaces:**
- Produces:
  - `upsert_account(id, name, strategy, symbol, timeframe, interval_seconds, starting_cash, ai_enabled, enabled, params: dict) -> None`
  - `list_accounts() -> list[dict]` (todas las columnas, orden por `id`)
  - `get_account(id) -> dict | None`
  - `set_account_enabled(id, enabled: bool) -> None`

- [ ] **Step 1: Test que falla**

```python
# tests/test_store_accounts.py
from __future__ import annotations

from bot.store.db import Store


def _seed(s):
    s.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                     10000.0, True, True, {"fast": 2, "slow": 4})


def test_account_crud():
    s = Store(":memory:")
    _seed(s)
    got = s.get_account("scalper")
    assert got["strategy"] == "ema_rsi" and got["params"] == {"fast": 2, "slow": 4}
    assert got["ai_enabled"] is True and got["interval_seconds"] == 12
    s.upsert_account("scalper", "Scalper 2", "ema_rsi", "BTC/USDT", "1m", 15,
                     10000.0, True, True, {"fast": 3, "slow": 8})
    assert s.get_account("scalper")["name"] == "Scalper 2"  # update, no duplica
    assert len(s.list_accounts()) == 1
    s.set_account_enabled("scalper", False)
    assert s.get_account("scalper")["enabled"] is False
    assert s.get_account("noexiste") is None
    s.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_accounts.py -q`
Expected: FAIL (`upsert_account` no existe).

- [ ] **Step 3: Agregar métodos de accounts a `Store`**

Agregar dentro de `Store` (antes de `close`):
```python
    # ---- accounts ----
    def upsert_account(
        self, id: str, name: str, strategy: str, symbol: str, timeframe: str,
        interval_seconds: int, starting_cash: float, ai_enabled: bool,
        enabled: bool, params: dict,
    ) -> None:
        values = dict(
            name=name, strategy=strategy, symbol=symbol, timeframe=timeframe,
            interval_seconds=interval_seconds, starting_cash=starting_cash,
            ai_enabled=ai_enabled, enabled=enabled, params=params,
        )
        with self._engine.begin() as conn:
            res = conn.execute(
                update(accounts).where(accounts.c.id == id).values(**values)
            )
            if res.rowcount == 0:
                conn.execute(insert(accounts).values(id=id, **values))

    def list_accounts(self) -> list[dict]:
        stmt = select(accounts).order_by(accounts.c.id)
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    def get_account(self, id: str) -> dict | None:
        stmt = select(accounts).where(accounts.c.id == id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        return None if row is None else dict(row._mapping)

    def set_account_enabled(self, id: str, enabled: bool) -> None:
        with self._engine.begin() as conn:
            conn.execute(update(accounts).where(accounts.c.id == id).values(enabled=enabled))
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_accounts.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add bot/store/db.py tests/test_store_accounts.py
git commit -m "feat(store): CRUD de la tabla accounts"
```

---

### Task 6: Cablear Engine, runner y CLI a `account="default"`

**Files:**
- Modify: `bot/engine/runner.py` (agregar `account` y pasarlo a cada llamada al store)
- Modify: `bot/cli.py` (`build_broker` y `_cmd_run`/`_cmd_status` usan `account="default"`)
- Test: `tests/test_engine_account.py` (nuevo) + correr los tests de engine existentes

**Interfaces:**
- Consumes: `Store` account-aware (Tasks 3-4).
- Produces: `Engine(..., account: str = "default")`; `Engine.account` atributo público; el runner usa `self.account` en `record_decision/record_fill/upsert_position/remove_position/record_equity/get_positions`. `build_broker(config, store, account="default")`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_engine_account.py
from __future__ import annotations

import pandas as pd

from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store


class _Feed:
    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        # 3 velas: la última se descarta (drop_forming_candle), decide sobre la previa.
        return pd.DataFrame({
            "timestamp": pd.to_datetime([1, 2, 3], unit="ms", utc=True),
            "open": [100, 100, 100], "high": [100, 100, 100],
            "low": [100, 100, 100], "close": [100, 100, 100], "volume": [1, 1, 1],
        })


class _Broker:
    def cash(self): return 10000.0


def _hold(df, params):
    return Signal(Action.HOLD, "sin señal", {"ema_fast": 1.0, "ema_slow": 2.0, "rsi": 50.0})


def test_engine_writes_under_its_account():
    store = Store(":memory:")
    eng = Engine(_Feed(), _Broker(), store, StrategyParams(), RiskParams(),
                 timeframe="1m", limit=3, decider=_hold, account="acc1")
    eng.run_cycle("BTC/USDT")
    assert len(store.recent_decisions("acc1")) == 1
    assert store.recent_decisions("default") == []
    store.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_engine_account.py -q`
Expected: FAIL (`Engine.__init__` no acepta `account`).

- [ ] **Step 3: Agregar `account` al Engine y pasarlo al store**

En `bot/engine/runner.py`:
1. En `Engine.__init__`, agregar parámetro `account: str = "default"` (después de `ai_affects_execution`) y `self.account = account`.
2. En `run_cycle`, reemplazar cada llamada al store por su versión con `self.account` como primer argumento:
   - `self.store.get_positions()` → `self.store.get_positions(self.account)`
   - `self.store.record_decision(ts, symbol, ...)` → `self.store.record_decision(self.account, ts, symbol, ...)`
   - `self.store.record_fill(ts, fill)` → `self.store.record_fill(self.account, ts, fill)`
   - `self.store.remove_position(symbol)` → `self.store.remove_position(self.account, symbol)`
   - `self.store.upsert_position(new_pos, ts)` → `self.store.upsert_position(self.account, new_pos, ts)`
3. En `_equity`, `self.store.get_positions()` → `self.store.get_positions(self.account)`.
4. En `_snapshot`, `self.store.record_equity(ts, equity, ...)` → `self.store.record_equity(self.account, ts, equity, ...)`.

- [ ] **Step 4: Actualizar `bot/cli.py`**

En `bot/cli.py`:
1. `build_broker(config, store=None)` → `build_broker(config, store=None, account="default")`; dentro, `store.latest_equity()` → `store.latest_equity(account)` y `store.get_positions()` → `store.get_positions(account)`.
2. En `_cmd_run`: pasar `account="default"` a `build_broker(config, store, account="default")` y agregar `account="default"` al `Engine(...)`.
3. En `_cmd_status`: `store.latest_equity()` → `store.latest_equity("default")`, `store.get_positions()` → `store.get_positions("default")`, `store.recent_decisions(limit=5)` → `store.recent_decisions("default", limit=5)`.

- [ ] **Step 5: Verificar verde (nuevo + engine existente)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_engine_account.py tests/ -q -k "engine or store or cli"` → PASS
(Si algún test viejo de engine/cli usa la firma vieja del store, actualizarlo para pasar `account` / `"default"`.)

- [ ] **Step 6: Commit**

```bash
git add bot/engine/runner.py bot/cli.py tests/test_engine_account.py
git commit -m "feat(engine): Engine y CLI operan bajo account=default"
```

---

### Task 7: API account-aware + `/api/accounts`

**Files:**
- Modify: `api/app.py` (endpoints toman `?account=`, default `"default"`; nuevo `/api/accounts`)
- Modify: `api/models.py` (nuevo `AccountOut`)
- Test: `tests/test_api_accounts.py` + actualizar `tests/test_api_live.py` y demás API tests para pasar el store account-aware

**Interfaces:**
- Consumes: `Store` account-aware; `store.list_accounts()`.
- Produces: cada endpoint de datos acepta `account: str = "default"` y lo pasa al store. `GET /api/accounts -> list[AccountOut]`. `AccountOut(id, name, strategy, symbol, timeframe, interval_seconds, ai_enabled, enabled, equity, cash)`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_api_accounts.py
from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_store
from bot.store.db import Store


def _client_with_store(store):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_accounts_listed_with_equity():
    store = Store(":memory:")
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2})
    store.record_equity("scalper", "2026-01-01T00:00:00+00:00", 10100.0, 9000.0)
    client = _client_with_store(store)
    r = client.get("/api/accounts")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["id"] == "scalper" and body[0]["equity"] == 10100.0


def test_status_scoped_by_account_query():
    store = Store(":memory:")
    store.record_equity("default", "2026-01-01T00:00:00+00:00", 10000.0, 10000.0)
    store.record_equity("other", "2026-01-01T00:00:00+00:00", 5000.0, 5000.0)
    client = _client_with_store(store)
    assert client.get("/api/status").json()["equity"] == 10000.0          # default
    assert client.get("/api/status?account=other").json()["equity"] == 5000.0
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_accounts.py -q`
Expected: FAIL (endpoints no aceptan `account`; no existe `/api/accounts`).

- [ ] **Step 3: Agregar `AccountOut` en `api/models.py`**

```python
class AccountOut(BaseModel):
    id: str
    name: str
    strategy: str
    symbol: str
    timeframe: str
    interval_seconds: int
    ai_enabled: bool
    enabled: bool
    equity: float
    cash: float
```

- [ ] **Step 4: Actualizar `api/app.py`**

1. Importar `AccountOut`.
2. En `status`, `equity`, `positions`, `decisions`, `fills`: agregar parámetro `account: str = "default"` y pasarlo a las llamadas del store (`store.latest_equity(account)`, `store.equity_series(account, limit)`, `store.get_positions(account)`, `store.recent_decisions(account, limit)`, `store.recent_fills(account, limit)`). En `status`, `recent = store.recent_decisions(account, 1)`.
3. (`/api/candles` no cambia: no usa el store.)
4. Nuevo endpoint:
```python
    @app.get("/api/accounts", response_model=list[AccountOut])
    def accounts_list(store: Store = Depends(get_store)) -> list[AccountOut]:
        out: list[AccountOut] = []
        for a in store.list_accounts():
            eq = store.latest_equity(a["id"])
            equity_v, cash = eq if eq is not None else (a["starting_cash"], a["starting_cash"])
            out.append(AccountOut(
                id=a["id"], name=a["name"], strategy=a["strategy"], symbol=a["symbol"],
                timeframe=a["timeframe"], interval_seconds=a["interval_seconds"],
                ai_enabled=a["ai_enabled"], enabled=a["enabled"],
                equity=equity_v, cash=cash,
            ))
        return out
```

- [ ] **Step 5: Actualizar tests de API existentes**

En `tests/test_api_live.py` y cualquier test que llame al store directamente: las inserciones de equity/decisiones ahora requieren `account` (usar `"default"`). Ej.: `store.record_equity("default", ts, 10000.0, 10000.0)`. Ajustar hasta que toda la suite quede verde.

- [ ] **Step 6: Verificar toda la suite verde**

Run: `.venv/Scripts/python.exe -m pytest -q` → PASS (todos)

- [ ] **Step 7: Commit**

```bash
git add api/app.py api/models.py tests/test_api_accounts.py tests/test_api_live.py
git commit -m "feat(api): endpoints account-aware (?account=) y GET /api/accounts"
```

---

### Task 8: Migración de datos viejos + semilla cuenta `default`

**Files:**
- Modify: `bot/store/db.py` (método privado `_migrate_legacy()` llamado en `__init__` tras `create_all`)
- Test: `tests/test_store_migration.py`

**Interfaces:**
- Produces: al abrir un SQLite con el esquema viejo (tablas sin columna `account`), `Store` agrega la columna `account` con default `'default'` a `decisions/fills/positions/equity` y rellena las filas existentes con `'default'`. Idempotente. Solo aplica a SQLite (en Postgres se arranca de cero).

- [ ] **Step 1: Test que falla**

```python
# tests/test_store_migration.py
from __future__ import annotations

import sqlite3

from bot.store.db import Store


def test_legacy_sqlite_rows_get_default_account(tmp_path):
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE equity (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, equity REAL, cash REAL);"
        "INSERT INTO equity (ts, equity, cash) VALUES ('2026-01-01T00:00:00+00:00', 10000.0, 10000.0);"
    )
    con.commit()
    con.close()

    s = Store(str(db))
    assert s.latest_equity("default") == (10000.0, 10000.0)
    s.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_migration.py -q`
Expected: FAIL (la fila vieja no tiene `account`; `create_all` no la migra, y la query por `account='default'` no la encuentra).

- [ ] **Step 3: Implementar la migración**

En `bot/store/db.py`, importar `text` de sqlalchemy e `inspect`:
```python
from sqlalchemy import delete, insert, inspect, select, text, update
```
En `Store.__init__`, después de `metadata.create_all(self._engine)`, llamar `self._migrate_legacy()`. Agregar el método:
```python
    def _migrate_legacy(self) -> None:
        # Solo SQLite: agrega la columna `account` (default 'default') a tablas
        # creadas con el esquema viejo y rellena las filas existentes.
        if self._engine.dialect.name != "sqlite":
            return
        insp = inspect(self._engine)
        for table in ("decisions", "fills", "positions", "equity"):
            cols = {c["name"] for c in insp.get_columns(table)}
            if "account" not in cols:
                with self._engine.begin() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN account TEXT NOT NULL DEFAULT 'default'"
                    ))
```
Nota: SQLite permite `ADD COLUMN ... NOT NULL DEFAULT`, que además rellena las filas existentes con `'default'`. `create_all` no toca tablas ya existentes, por eso la columna podía faltar.

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_store_migration.py -q` → PASS

- [ ] **Step 5: Suite completa + commit**

Run: `.venv/Scripts/python.exe -m pytest -q` → PASS (todos)
```bash
git add bot/store/db.py tests/test_store_migration.py
git commit -m "feat(store): migra DB vieja a account=default (idempotente, SQLite)"
```

---

## Notas de cierre

- Tras la Fase 1, la cuenta única sigue operando exactamente igual (todo bajo `account="default"`), pero el `Store`, el `Engine`, la CLI y la API ya entienden `account`, y la DB corre en SQLite o Postgres según `DATABASE_URL`.
- La tabla `accounts` queda creada y con CRUD, lista para que la **Fase 3 (flota)** siembre las 5 cuentas y lance un hilo por cada una.
- **Fuera de alcance de esta fase** (van en fases siguientes): estrategias nuevas (Fase 2), orquestador de hilos + un solo contenedor (Fase 3), panel multi-cuenta y edición de config (Fase 4).
