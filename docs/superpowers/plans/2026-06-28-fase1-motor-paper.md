# Fase 1 — Motor de paper trading — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el bot AMÉRICO **opere en paper**: a partir de la decisión (Fase 0), ejecutar órdenes simuladas con gestión de riesgo, persistir el estado en SQLite y correr en un loop — con dos brokers (paper local y OKX Demo) detrás de una sola interfaz, elegibles por config.

**Architecture:** Se construye sobre el núcleo de Fase 0 (`DataFeed → indicadores → estrategia → Signal`). Se agrega: un fix para decidir sobre la **última vela cerrada**; una interfaz `Broker` con dos implementaciones (`LocalPaperBroker`, `OkxDemoBroker`); un `RiskManager` (funciones puras de sizing y stop/take); un `Store` (SQLite, stdlib) para decisiones/fills/posiciones/equity; y un `Engine` que orquesta un ciclo y un loop. El broker solo ejecuta y reporta caja; las posiciones (con entrada, stop-loss y take-profit) las trackea el `Store`/`Engine`. La estrategia se inyecta en el `Engine` para poder testear el orquestador de forma determinista.

**Tech Stack:** Python 3.11+, `ccxt` (ya presente, para OKX Demo y datos), `pandas` (ya presente), `sqlite3` + `datetime` (stdlib), `pytest`. No se agregan dependencias nuevas.

## Global Constraints

- **Python `>=3.11`.** No se agregan dependencias nuevas (todo es stdlib o ya instalado: `ccxt`, `pandas`, `PyYAML`, `pytest`).
- **Ejecutar Python con el venv del proyecto:** en Windows `.venv/Scripts/python.exe` (o activar el venv). Los comandos de abajo escriben `python` por brevedad; el ejecutor usa el intérprete del venv.
- **Tests unitarios sin red:** ningún test llama a un exchange real. `OkxDemoBroker` se testea con un exchange falso inyectado; el `Engine` con una estrategia, un feed y un broker falsos/locales. La red solo aparece en la corrida manual de la última task.
- **Decidir sobre la última vela CERRADA:** antes de evaluar la estrategia, descartar la vela en formación (`drop_forming_candle`). (Esto corrige el hallazgo del review de Fase 0.)
- **Spot long-only en v1:** una posición por símbolo, cantidad positiva.
- **El broker solo ejecuta y reporta caja** (`cash()`); las posiciones con stop-loss/take-profit las mantiene el `Store`/`Engine`, no el broker.
- **Claves nunca en el repo:** las API keys de OKX Demo se leen de variables de entorno (`OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSWORD`), nunca de `config.yaml`.
- **Identificadores y mensajes de commit en inglés;** textos visibles al usuario (logs, motivos) en español.
- **Cada commit termina con el trailer** (segundo `-m`): `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Fuera de alcance de v1 (se difiere a una fase posterior):** circuit breaker por drawdown diario, reconciliación de posiciones contra el balance real del exchange, y la equity multi-símbolo exacta (en v1, al valuar equity, las posiciones de otros símbolos se valúan a su precio de entrada).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `bot/data/feed.py` (modificar) | + `drop_forming_candle(df)` |
| `bot/cli.py` (modificar) | aplicar `drop_forming_candle` en `run_decide`; + `run`/`status`/`build_broker` |
| `bot/config.py` (modificar) | + `BrokerParams`, `RiskParams`, campos nuevos de `Config`, parsing |
| `config.yaml` (modificar) | + secciones `broker:` y `risk:`, `db_path`, `limit`, `loop_interval_seconds` |
| `bot/broker/__init__.py` | paquete |
| `bot/broker/models.py` | `Side`, `Fill`, `Position` |
| `bot/broker/base.py` | `Broker` (Protocol) |
| `bot/broker/paper.py` | `LocalPaperBroker` |
| `bot/broker/okx_demo.py` | `OkxDemoBroker` |
| `bot/risk/__init__.py` | paquete |
| `bot/risk/manager.py` | `size_quantity`, `stop_loss_price`, `take_profit_price`, `can_open` |
| `bot/store/__init__.py` | paquete |
| `bot/store/db.py` | `Store` (SQLite) |
| `bot/engine/__init__.py` | paquete |
| `bot/engine/runner.py` | `CycleResult`, `Engine` (`run_cycle`, `run_loop`) |
| `tests/...` | tests por módulo |

---

### Task 1: Fix de la vela cerrada (`drop_forming_candle`)

**Files:**
- Modify: `bot/data/feed.py`
- Modify: `bot/cli.py` (aplicarlo en `run_decide`)
- Test: `tests/test_feed.py` (agregar test)

**Interfaces:**
- Produces: `drop_forming_candle(df: pd.DataFrame) -> pd.DataFrame` (devuelve `df` sin la última fila — la vela en formación).

- [ ] **Step 1: Agregar el test que falla** — añadir a `tests/test_feed.py`:

```python
from bot.data.feed import drop_forming_candle


def test_drop_forming_candle_removes_last_row():
    rows = [
        [1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0],
        [1700003600000, 1.5, 2.5, 1.0, 2.0, 12.0],
        [1700007200000, 2.0, 3.0, 1.5, 2.5, 14.0],
    ]
    df = ohlcv_to_df(rows)
    closed = drop_forming_candle(df)
    assert len(closed) == 2
    assert closed["close"].iloc[-1] == 2.0
```

(El import `ohlcv_to_df` ya existe en ese archivo de test.)

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_feed.py::test_drop_forming_candle_removes_last_row -q`
Expected: FAIL con `ImportError: cannot import name 'drop_forming_candle'`.

- [ ] **Step 3: Implementar** — agregar a `bot/data/feed.py` (debajo de `ohlcv_to_df`):

```python
def drop_forming_candle(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1]
```

- [ ] **Step 4: Usarlo en `run_decide`** — en `bot/cli.py`, cambiar el cuerpo de `run_decide` para descartar la vela en formación. Reemplazar:

```python
    df = feed.fetch_ohlcv(symbol, timeframe, limit)
    return evaluate(df, config.strategy)
```

por:

```python
    df = drop_forming_candle(feed.fetch_ohlcv(symbol, timeframe, limit))
    return evaluate(df, config.strategy)
```

y actualizar el import en `bot/cli.py`:

```python
from bot.data.feed import CcxtDataFeed, DataFeed, drop_forming_candle
```

- [ ] **Step 5: Run y verificar verde**

Run: `python -m pytest tests/test_feed.py tests/test_cli.py -q`
Expected: PASS (el test nuevo + los de cli siguen verdes; `uptrend_df` con 80 filas pierde 1 y sigue produciendo un `Signal`).

- [ ] **Step 6: Commit**

```bash
git add bot/data/feed.py bot/cli.py tests/test_feed.py
git commit -m "feat: decide on last closed candle (drop forming candle)"
```

---

### Task 2: Config extendida (`BrokerParams`, `RiskParams`, campos nuevos)

**Files:**
- Modify: `bot/config.py`
- Modify: `config.yaml`
- Test: `tests/test_config.py` (agregar tests)

**Interfaces:**
- Produces:
  - `@dataclass BrokerParams` con `kind:str="paper"`, `paper_cash:float=10000.0`, `fee_rate:float=0.001`, `slippage:float=0.0005`.
  - `@dataclass RiskParams` con `risk_per_trade:float=0.01`, `stop_loss_pct:float=0.02`, `take_profit_pct:float=0.04`, `max_exposure_pct:float=0.30`, `max_positions:int=3`.
  - `Config` con campos adicionales: `limit:int=200`, `db_path:str="americo.sqlite"`, `loop_interval_seconds:int=3600`, `broker:BrokerParams`, `risk:RiskParams`.
  - `load_config` parsea las secciones `broker:` y `risk:` con defaults.

- [ ] **Step 1: Agregar los tests que fallan** — añadir a `tests/test_config.py`:

```python
from bot.config import BrokerParams, RiskParams


def test_load_config_reads_broker_and_risk(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "db_path: data.sqlite\n"
        "limit: 300\n"
        "broker:\n"
        "  kind: okx_demo\n"
        "  paper_cash: 5000\n"
        "risk:\n"
        "  risk_per_trade: 0.02\n"
        "  max_positions: 5\n",
        encoding="utf-8",
    )
    c = load_config(p)
    assert c.db_path == "data.sqlite"
    assert c.limit == 300
    assert c.broker.kind == "okx_demo"
    assert c.broker.paper_cash == 5000
    assert c.broker.fee_rate == 0.001  # default conservado
    assert c.risk.risk_per_trade == 0.02
    assert c.risk.max_positions == 5
    assert c.risk.stop_loss_pct == 0.02  # default conservado


def test_broker_and_risk_defaults_on_empty(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("{}", encoding="utf-8")
    c = load_config(p)
    assert c.broker == BrokerParams()
    assert c.risk == RiskParams()
    assert c.db_path == "americo.sqlite"
    assert c.loop_interval_seconds == 3600
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL con `ImportError: cannot import name 'BrokerParams'`.

- [ ] **Step 3: Implementar** — reemplazar **todo** el contenido de `bot/config.py` por:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class StrategyParams:
    fast: int = 20
    slow: int = 50
    rsi_period: int = 14
    rsi_oversold: float = 35.0
    rsi_overbought: float = 70.0


@dataclass
class BrokerParams:
    kind: str = "paper"  # "paper" | "okx_demo"
    paper_cash: float = 10000.0
    fee_rate: float = 0.001
    slippage: float = 0.0005


@dataclass
class RiskParams:
    risk_per_trade: float = 0.01
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    max_exposure_pct: float = 0.30
    max_positions: int = 3


@dataclass
class Config:
    exchange: str = "okx"
    timeframe: str = "1h"
    symbols: list[str] = field(default_factory=lambda: ["BTC/USDT"])
    limit: int = 200
    db_path: str = "americo.sqlite"
    loop_interval_seconds: int = 3600
    strategy: StrategyParams = field(default_factory=StrategyParams)
    broker: BrokerParams = field(default_factory=BrokerParams)
    risk: RiskParams = field(default_factory=RiskParams)


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    strat = data.get("strategy") or {}
    brk = data.get("broker") or {}
    rsk = data.get("risk") or {}
    return Config(
        exchange=data.get("exchange", "okx"),
        timeframe=data.get("timeframe", "1h"),
        symbols=data.get("symbols", ["BTC/USDT"]),
        limit=data.get("limit", 200),
        db_path=data.get("db_path", "americo.sqlite"),
        loop_interval_seconds=data.get("loop_interval_seconds", 3600),
        strategy=StrategyParams(
            fast=strat.get("fast", 20),
            slow=strat.get("slow", 50),
            rsi_period=strat.get("rsi_period", 14),
            rsi_oversold=strat.get("rsi_oversold", 35.0),
            rsi_overbought=strat.get("rsi_overbought", 70.0),
        ),
        broker=BrokerParams(
            kind=brk.get("kind", "paper"),
            paper_cash=brk.get("paper_cash", 10000.0),
            fee_rate=brk.get("fee_rate", 0.001),
            slippage=brk.get("slippage", 0.0005),
        ),
        risk=RiskParams(
            risk_per_trade=rsk.get("risk_per_trade", 0.01),
            stop_loss_pct=rsk.get("stop_loss_pct", 0.02),
            take_profit_pct=rsk.get("take_profit_pct", 0.04),
            max_exposure_pct=rsk.get("max_exposure_pct", 0.30),
            max_positions=rsk.get("max_positions", 3),
        ),
    )
```

- [ ] **Step 4: Actualizar `config.yaml`** — reemplazar todo su contenido por:

```yaml
exchange: okx
timeframe: "1h"
symbols:
  - BTC/USDT
  - ETH/USDT
limit: 200
db_path: americo.sqlite
loop_interval_seconds: 3600
strategy:
  fast: 20
  slow: 50
  rsi_period: 14
  rsi_oversold: 35
  rsi_overbought: 70
broker:
  kind: paper          # paper | okx_demo
  paper_cash: 10000
  fee_rate: 0.001
  slippage: 0.0005
risk:
  risk_per_trade: 0.01
  stop_loss_pct: 0.02
  take_profit_pct: 0.04
  max_exposure_pct: 0.30
  max_positions: 3
```

- [ ] **Step 5: Run y verificar verde**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS (los 2 tests viejos + los 2 nuevos). Luego corré la suite completa `python -m pytest -q` (todo verde).

- [ ] **Step 6: Commit**

```bash
git add bot/config.py config.yaml tests/test_config.py
git commit -m "feat: extend config with broker and risk params"
```

---

### Task 3: Modelos de trading + interfaz `Broker`

**Files:**
- Create: `bot/broker/__init__.py` (vacío), `bot/broker/models.py`, `bot/broker/base.py`
- Test: `tests/test_broker_models.py`

**Interfaces:**
- Produces:
  - `class Side(str, Enum)` con `BUY`, `SELL`.
  - `@dataclass(frozen=True) class Fill` con `symbol:str`, `side:Side`, `quantity:float`, `price:float`, `fee:float`.
  - `@dataclass class Position` con `symbol:str`, `quantity:float`, `entry_price:float`, `stop_loss:float`, `take_profit:float`.
  - `class Broker(Protocol)` con `buy(symbol, quantity, ref_price) -> Fill`, `sell(symbol, quantity, ref_price) -> Fill`, `cash() -> float`.

- [ ] **Step 1: Crear `bot/broker/__init__.py`** (archivo vacío).

- [ ] **Step 2: Escribir el test que falla** — `tests/test_broker_models.py`:

```python
from bot.broker.models import Fill, Position, Side


def test_fill_fields():
    f = Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05)
    assert f.side is Side.BUY
    assert f.quantity == 0.5
    assert f.price == 100.0
    assert f.fee == 0.05


def test_position_fields():
    p = Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0)
    assert p.stop_loss == 98.0
    assert p.take_profit == 104.0


def test_side_values():
    assert {s.value for s in Side} == {"BUY", "SELL"}
```

- [ ] **Step 3: Run para verificar que falla**

Run: `python -m pytest tests/test_broker_models.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.broker.models'`.

- [ ] **Step 4: Implementar `bot/broker/models.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Fill:
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
```

y `bot/broker/base.py`:

```python
from __future__ import annotations

from typing import Protocol

from bot.broker.models import Fill


class Broker(Protocol):
    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill: ...
    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill: ...
    def cash(self) -> float: ...
```

- [ ] **Step 5: Run y verificar verde**

Run: `python -m pytest tests/test_broker_models.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add bot/broker/__init__.py bot/broker/models.py bot/broker/base.py tests/test_broker_models.py
git commit -m "feat: add trading models and Broker interface"
```

---

### Task 4: `LocalPaperBroker`

**Files:**
- Create: `bot/broker/paper.py`
- Test: `tests/test_paper_broker.py`

**Interfaces:**
- Consumes: `bot.broker.models.Fill`, `bot.broker.models.Side`.
- Produces: `class LocalPaperBroker` con `__init__(cash, fee_rate=0.001, slippage=0.0005)`, `cash() -> float`, `holdings(symbol) -> float`, `buy(symbol, quantity, ref_price) -> Fill`, `sell(symbol, quantity, ref_price) -> Fill`. Aplica slippage (`buy` a `ref_price*(1+slippage)`, `sell` a `ref_price*(1-slippage)`) y comisión (`fee_rate` sobre el notional). Lanza `ValueError` si no hay saldo (buy) o no hay posición suficiente (sell).

- [ ] **Step 1: Escribir el test que falla** — `tests/test_paper_broker.py`:

```python
import pytest

from bot.broker.models import Side
from bot.broker.paper import LocalPaperBroker


def test_buy_deducts_cash_with_fee_and_slippage():
    b = LocalPaperBroker(cash=10000.0, fee_rate=0.001, slippage=0.0005)
    fill = b.buy("BTC/USDT", 0.1, ref_price=100.0)
    assert fill.side is Side.BUY
    assert abs(fill.price - 100.05) < 1e-9          # 100 * (1 + 0.0005)
    assert abs(fill.fee - 0.010005) < 1e-9          # 0.1*100.05*0.001
    assert abs(b.cash() - 9989.984995) < 1e-6       # 10000 - (10.005 + 0.010005)
    assert abs(b.holdings("BTC/USDT") - 0.1) < 1e-12


def test_sell_adds_cash_and_reduces_holdings():
    b = LocalPaperBroker(cash=10000.0, fee_rate=0.001, slippage=0.0005)
    b.buy("BTC/USDT", 0.1, ref_price=100.0)
    fill = b.sell("BTC/USDT", 0.1, ref_price=110.0)
    assert fill.side is Side.SELL
    assert abs(fill.price - 109.945) < 1e-9          # 110 * (1 - 0.0005)
    assert abs(b.cash() - 10000.9685005) < 1e-6
    assert abs(b.holdings("BTC/USDT")) < 1e-12


def test_buy_without_cash_raises():
    b = LocalPaperBroker(cash=5.0)
    with pytest.raises(ValueError):
        b.buy("BTC/USDT", 1.0, ref_price=100.0)


def test_sell_without_position_raises():
    b = LocalPaperBroker(cash=10000.0)
    with pytest.raises(ValueError):
        b.sell("BTC/USDT", 1.0, ref_price=100.0)
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_paper_broker.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.broker.paper'`.

- [ ] **Step 3: Implementar `bot/broker/paper.py`:**

```python
from __future__ import annotations

from bot.broker.models import Fill, Side


class LocalPaperBroker:
    def __init__(self, cash: float, fee_rate: float = 0.001, slippage: float = 0.0005) -> None:
        self._cash = float(cash)
        self.fee_rate = fee_rate
        self.slippage = slippage
        self._holdings: dict[str, float] = {}

    def cash(self) -> float:
        return self._cash

    def holdings(self, symbol: str) -> float:
        return self._holdings.get(symbol, 0.0)

    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        fill_price = ref_price * (1 + self.slippage)
        cost = quantity * fill_price
        fee = cost * self.fee_rate
        total = cost + fee
        if total > self._cash + 1e-9:
            raise ValueError(
                f"Saldo insuficiente: necesita {total:.2f}, tiene {self._cash:.2f}"
            )
        self._cash -= total
        self._holdings[symbol] = self._holdings.get(symbol, 0.0) + quantity
        return Fill(symbol, Side.BUY, quantity, fill_price, fee)

    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        held = self._holdings.get(symbol, 0.0)
        if quantity > held + 1e-9:
            raise ValueError(
                f"Posición insuficiente en {symbol}: vende {quantity}, tiene {held}"
            )
        fill_price = ref_price * (1 - self.slippage)
        proceeds = quantity * fill_price
        fee = proceeds * self.fee_rate
        self._cash += proceeds - fee
        self._holdings[symbol] = held - quantity
        return Fill(symbol, Side.SELL, quantity, fill_price, fee)
```

- [ ] **Step 4: Run y verificar verde**

Run: `python -m pytest tests/test_paper_broker.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/broker/paper.py tests/test_paper_broker.py
git commit -m "feat: add LocalPaperBroker with fees and slippage"
```

---

### Task 5: `OkxDemoBroker`

**Files:**
- Create: `bot/broker/okx_demo.py`
- Test: `tests/test_okx_broker.py`

**Interfaces:**
- Consumes: `bot.broker.models.Fill`, `bot.broker.models.Side`.
- Produces: `class OkxDemoBroker` con `__init__(api_key, secret, password, quote="USDT", exchange=None)` (si `exchange is None`, construye `ccxt.okx` con las claves y `set_sandbox_mode(True)`; si se inyecta `exchange`, lo usa — para tests sin red), `cash() -> float` (free balance de `quote`), `buy/sell(symbol, quantity, ref_price) -> Fill` (vía `create_market_*_order`; `ref_price` se ignora porque el fill viene del exchange).

- [ ] **Step 1: Escribir el test que falla** — `tests/test_okx_broker.py`:

```python
from bot.broker.models import Side
from bot.broker.okx_demo import OkxDemoBroker


class FakeExchange:
    def __init__(self):
        self.calls = []

    def create_market_buy_order(self, symbol, quantity):
        self.calls.append(("buy", symbol, quantity))
        return {"average": 100.0, "filled": quantity, "fee": {"cost": 0.1}}

    def create_market_sell_order(self, symbol, quantity):
        self.calls.append(("sell", symbol, quantity))
        return {"average": 110.0, "filled": quantity, "fee": {"cost": 0.11}}

    def fetch_balance(self):
        return {"free": {"USDT": 5000.0}}


def test_buy_calls_exchange_and_parses_fill():
    ex = FakeExchange()
    b = OkxDemoBroker("k", "s", "p", exchange=ex)
    fill = b.buy("BTC/USDT", 0.5, ref_price=0.0)
    assert ex.calls == [("buy", "BTC/USDT", 0.5)]
    assert fill.side is Side.BUY
    assert fill.price == 100.0
    assert fill.quantity == 0.5
    assert fill.fee == 0.1


def test_sell_calls_exchange_and_parses_fill():
    ex = FakeExchange()
    b = OkxDemoBroker("k", "s", "p", exchange=ex)
    fill = b.sell("BTC/USDT", 0.5, ref_price=0.0)
    assert ex.calls == [("sell", "BTC/USDT", 0.5)]
    assert fill.side is Side.SELL
    assert fill.price == 110.0
    assert fill.fee == 0.11


def test_cash_reads_free_quote_balance():
    b = OkxDemoBroker("k", "s", "p", exchange=FakeExchange())
    assert b.cash() == 5000.0
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_okx_broker.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.broker.okx_demo'`.

- [ ] **Step 3: Implementar `bot/broker/okx_demo.py`:**

```python
from __future__ import annotations

from typing import Any

from bot.broker.models import Fill, Side


class OkxDemoBroker:
    def __init__(
        self,
        api_key: str,
        secret: str,
        password: str,
        quote: str = "USDT",
        exchange: Any | None = None,
    ) -> None:
        self.quote = quote
        if exchange is None:
            import ccxt

            exchange = ccxt.okx(
                {
                    "apiKey": api_key,
                    "secret": secret,
                    "password": password,
                    "enableRateLimit": True,
                }
            )
            exchange.set_sandbox_mode(True)
        self._exchange = exchange

    def cash(self) -> float:
        balance = self._exchange.fetch_balance()
        return float(balance["free"].get(self.quote, 0.0))

    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        order = self._exchange.create_market_buy_order(symbol, quantity)
        return self._to_fill(order, symbol, Side.BUY)

    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        order = self._exchange.create_market_sell_order(symbol, quantity)
        return self._to_fill(order, symbol, Side.SELL)

    @staticmethod
    def _to_fill(order: dict, symbol: str, side: Side) -> Fill:
        price = float(order.get("average") or order.get("price") or 0.0)
        quantity = float(order.get("filled") or order.get("amount") or 0.0)
        fee_info = order.get("fee") or {}
        fee = float(fee_info.get("cost") or 0.0)
        return Fill(symbol, side, quantity, price, fee)
```

- [ ] **Step 4: Run y verificar verde**

Run: `python -m pytest tests/test_okx_broker.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/broker/okx_demo.py tests/test_okx_broker.py
git commit -m "feat: add OkxDemoBroker over ccxt sandbox"
```

---

### Task 6: `RiskManager`

**Files:**
- Create: `bot/risk/__init__.py` (vacío), `bot/risk/manager.py`
- Test: `tests/test_risk.py`

**Interfaces:**
- Consumes: `bot.config.RiskParams`.
- Produces (todas funciones puras):
  - `size_quantity(equity: float, price: float, params: RiskParams) -> float` (cantidad por riesgo: `equity*risk_per_trade / (price*stop_loss_pct)`, topeada para que el notional no supere `equity*max_exposure_pct`; si `price*stop_loss_pct <= 0`, devuelve `0.0`).
  - `stop_loss_price(entry: float, params: RiskParams) -> float` (`entry*(1-stop_loss_pct)`).
  - `take_profit_price(entry: float, params: RiskParams) -> float` (`entry*(1+take_profit_pct)`).
  - `can_open(open_positions: int, params: RiskParams) -> bool` (`open_positions < max_positions`).

- [ ] **Step 1: Crear `bot/risk/__init__.py`** (archivo vacío).

- [ ] **Step 2: Escribir el test que falla** — `tests/test_risk.py`:

```python
from bot.config import RiskParams
from bot.risk.manager import can_open, size_quantity, stop_loss_price, take_profit_price


def test_size_quantity_capped_by_max_exposure():
    p = RiskParams(risk_per_trade=0.01, stop_loss_pct=0.02, max_exposure_pct=0.30)
    # riesgo: 100 / (100*0.02)=50 -> notional 5000 > 3000 -> topea a 30
    assert abs(size_quantity(10000.0, 100.0, p) - 30.0) < 1e-9


def test_size_quantity_not_capped():
    p = RiskParams(risk_per_trade=0.01, stop_loss_pct=0.10, max_exposure_pct=0.30)
    # 100 / (100*0.10)=10 -> notional 1000 < 3000 -> 10
    assert abs(size_quantity(10000.0, 100.0, p) - 10.0) < 1e-9


def test_stop_and_take_prices():
    p = RiskParams(stop_loss_pct=0.02, take_profit_pct=0.04)
    assert abs(stop_loss_price(100.0, p) - 98.0) < 1e-9
    assert abs(take_profit_price(100.0, p) - 104.0) < 1e-9


def test_can_open_respects_max_positions():
    p = RiskParams(max_positions=3)
    assert can_open(2, p) is True
    assert can_open(3, p) is False
```

- [ ] **Step 3: Run para verificar que falla**

Run: `python -m pytest tests/test_risk.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.risk.manager'`.

- [ ] **Step 4: Implementar `bot/risk/manager.py`:**

```python
from __future__ import annotations

from bot.config import RiskParams


def size_quantity(equity: float, price: float, params: RiskParams) -> float:
    per_unit_risk = price * params.stop_loss_pct
    if per_unit_risk <= 0:
        return 0.0
    risk_amount = equity * params.risk_per_trade
    quantity = risk_amount / per_unit_risk
    max_notional = equity * params.max_exposure_pct
    if quantity * price > max_notional:
        quantity = max_notional / price
    return quantity


def stop_loss_price(entry: float, params: RiskParams) -> float:
    return entry * (1 - params.stop_loss_pct)


def take_profit_price(entry: float, params: RiskParams) -> float:
    return entry * (1 + params.take_profit_pct)


def can_open(open_positions: int, params: RiskParams) -> bool:
    return open_positions < params.max_positions
```

- [ ] **Step 5: Run y verificar verde**

Run: `python -m pytest tests/test_risk.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add bot/risk/__init__.py bot/risk/manager.py tests/test_risk.py
git commit -m "feat: add risk manager (sizing, stop/take, limits)"
```

---

### Task 7: `Store` (persistencia SQLite)

**Files:**
- Create: `bot/store/__init__.py` (vacío), `bot/store/db.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `bot.broker.models.Fill`, `bot.broker.models.Position`, `sqlite3` (stdlib).
- Produces: `class Store` con `__init__(path=":memory:")` (crea el esquema), y métodos:
  - `record_decision(ts, symbol, action, reason, ema_fast, ema_slow, rsi) -> None`
  - `recent_decisions(limit=10) -> list[dict]` (más reciente primero; claves `ts,symbol,action,reason`)
  - `record_fill(ts, fill: Fill) -> None`
  - `upsert_position(pos: Position, opened_at: str) -> None`
  - `remove_position(symbol: str) -> None`
  - `get_positions() -> dict[str, Position]`
  - `record_equity(ts, equity, cash) -> None`
  - `latest_equity() -> tuple[float, float] | None` (`(equity, cash)` o `None`)

- [ ] **Step 1: Escribir el test que falla** — `tests/test_store.py`:

```python
from bot.broker.models import Fill, Position, Side
from bot.store.db import Store


def test_decisions_round_trip():
    s = Store(":memory:")
    s.record_decision("t1", "BTC/USDT", "HOLD", "sin señal", 1.0, 2.0, 50.0)
    s.record_decision("t2", "BTC/USDT", "BUY", "cruce", 3.0, 2.0, 40.0)
    recent = s.recent_decisions(limit=10)
    assert len(recent) == 2
    assert recent[0]["action"] == "BUY"  # más reciente primero
    assert recent[0]["reason"] == "cruce"


def test_positions_upsert_get_remove():
    s = Store(":memory:")
    s.upsert_position(Position("BTC/USDT", 0.5, 100.0, 98.0, 104.0), "t1")
    pos = s.get_positions()
    assert set(pos) == {"BTC/USDT"}
    assert pos["BTC/USDT"].entry_price == 100.0
    s.upsert_position(Position("BTC/USDT", 0.7, 101.0, 99.0, 105.0), "t2")
    assert s.get_positions()["BTC/USDT"].quantity == 0.7  # actualiza, no duplica
    s.remove_position("BTC/USDT")
    assert s.get_positions() == {}


def test_fill_and_equity():
    s = Store(":memory:")
    s.record_fill("t1", Fill("BTC/USDT", Side.BUY, 0.5, 100.0, 0.05))
    assert s.latest_equity() is None
    s.record_equity("t1", 10000.0, 9000.0)
    s.record_equity("t2", 10100.0, 9100.0)
    assert s.latest_equity() == (10100.0, 9100.0)  # último
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_store.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.store.db'`.

- [ ] **Step 3: Implementar `bot/store/db.py`:**

```python
from __future__ import annotations

import sqlite3

from bot.broker.models import Fill, Position

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, symbol TEXT, action TEXT, reason TEXT,
    ema_fast REAL, ema_slow REAL, rsi REAL
);
CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, symbol TEXT, side TEXT, quantity REAL, price REAL, fee REAL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity REAL, entry_price REAL, stop_loss REAL, take_profit REAL, opened_at TEXT
);
CREATE TABLE IF NOT EXISTS equity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, equity REAL, cash REAL
);
"""


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def record_decision(
        self, ts: str, symbol: str, action: str, reason: str,
        ema_fast: float, ema_slow: float, rsi: float,
    ) -> None:
        self._conn.execute(
            "INSERT INTO decisions (ts,symbol,action,reason,ema_fast,ema_slow,rsi)"
            " VALUES (?,?,?,?,?,?,?)",
            (ts, symbol, action, reason, ema_fast, ema_slow, rsi),
        )
        self._conn.commit()

    def recent_decisions(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,symbol,action,reason FROM decisions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def record_fill(self, ts: str, fill: Fill) -> None:
        self._conn.execute(
            "INSERT INTO fills (ts,symbol,side,quantity,price,fee) VALUES (?,?,?,?,?,?)",
            (ts, fill.symbol, fill.side.value, fill.quantity, fill.price, fill.fee),
        )
        self._conn.commit()

    def upsert_position(self, pos: Position, opened_at: str) -> None:
        self._conn.execute(
            "INSERT INTO positions (symbol,quantity,entry_price,stop_loss,take_profit,opened_at)"
            " VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(symbol) DO UPDATE SET"
            " quantity=excluded.quantity, entry_price=excluded.entry_price,"
            " stop_loss=excluded.stop_loss, take_profit=excluded.take_profit",
            (pos.symbol, pos.quantity, pos.entry_price, pos.stop_loss, pos.take_profit, opened_at),
        )
        self._conn.commit()

    def remove_position(self, symbol: str) -> None:
        self._conn.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
        self._conn.commit()

    def get_positions(self) -> dict[str, Position]:
        rows = self._conn.execute(
            "SELECT symbol,quantity,entry_price,stop_loss,take_profit FROM positions"
        ).fetchall()
        return {
            r["symbol"]: Position(
                r["symbol"], r["quantity"], r["entry_price"], r["stop_loss"], r["take_profit"]
            )
            for r in rows
        }

    def record_equity(self, ts: str, equity: float, cash: float) -> None:
        self._conn.execute(
            "INSERT INTO equity (ts,equity,cash) VALUES (?,?,?)", (ts, equity, cash)
        )
        self._conn.commit()

    def latest_equity(self) -> tuple[float, float] | None:
        row = self._conn.execute(
            "SELECT equity,cash FROM equity ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else (row["equity"], row["cash"])
```

- [ ] **Step 4: Run y verificar verde**

Run: `python -m pytest tests/test_store.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/store/__init__.py bot/store/db.py tests/test_store.py
git commit -m "feat: add SQLite store for decisions, fills, positions, equity"
```

---

### Task 8: `Engine.run_cycle`

**Files:**
- Create: `bot/engine/__init__.py` (vacío), `bot/engine/runner.py`
- Test: `tests/test_engine_cycle.py`

**Interfaces:**
- Consumes: `bot.broker.base.Broker`, `bot.broker.models.Position`, `bot.config.RiskParams`, `bot.config.StrategyParams`, `bot.data.feed.DataFeed`, `bot.data.feed.drop_forming_candle`, `bot.models.Action`, `bot.models.Signal`, `bot.risk.manager.*`, `bot.store.db.Store`, `bot.strategy.ema_rsi.evaluate`.
- Produces:
  - `@dataclass class CycleResult` con `symbol:str`, `action:str`, `detail:str`.
  - `class Engine` con `__init__(feed, broker, store, strategy, risk, timeframe="1h", limit=200, clock=<utc iso>, log=print, decider=evaluate)` y `run_cycle(symbol) -> CycleResult`. La estrategia se inyecta vía `decider(df, strategy) -> Signal` (default `evaluate`) para poder testear el orquestador de forma determinista.
  - Lógica de `run_cycle`: descarta la vela en formación; `price = último close cerrado`; evalúa y registra la decisión; **primero** chequea salida por stop-loss/take-profit de la posición abierta; si no, aplica la acción (`BUY` abre con sizing + SL/TP si no hay posición y `can_open`; `SELL` cierra si hay posición); registra fills, posiciones y un snapshot de equity.

- [ ] **Step 1: Crear `bot/engine/__init__.py`** (archivo vacío).

- [ ] **Step 2: Escribir el test que falla** — `tests/test_engine_cycle.py`:

```python
from bot.broker.models import Position
from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store
from tests.conftest import make_df

CLOCK = lambda: "2024-01-01T00:00:00+00:00"


class FakeFeed:
    def __init__(self, df):
        self.df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self.df


def const_decider(action, rsi=50.0):
    def _decider(df, params):
        return Signal(action, "test", {"ema_fast": 1.0, "ema_slow": 1.0, "rsi": rsi})
    return _decider


def make_engine(feed, broker, store, decider):
    return Engine(
        feed=feed, broker=broker, store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        timeframe="1h", limit=200, clock=CLOCK, log=lambda m: None,
        decider=decider,
    )


def test_buy_opens_position_and_spends_cash():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))  # último cerrado = 59
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    engine = make_engine(feed, broker, store, const_decider(Action.BUY))
    result = engine.run_cycle("BTC/USDT")
    assert result.action == "BUY"
    assert "BTC/USDT" in store.get_positions()
    assert broker.cash() < 10000.0
    assert store.latest_equity() is not None


def test_sell_closes_existing_position():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    # primero abrir con un BUY
    make_engine(feed, broker, store, const_decider(Action.BUY)).run_cycle("BTC/USDT")
    cash_after_buy = broker.cash()
    # ahora vender
    make_engine(feed, broker, store, const_decider(Action.SELL)).run_cycle("BTC/USDT")
    assert store.get_positions() == {}
    assert broker.cash() > cash_after_buy


def test_stop_loss_exit_when_price_below_stop():
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    # abrir a precio alto
    feed = FakeFeed(make_df([100.0, 100.0, 100.0]))   # último cerrado = 100
    make_engine(feed, broker, store, const_decider(Action.BUY)).run_cycle("BTC/USDT")
    assert "BTC/USDT" in store.get_positions()
    # precio se desploma por debajo del stop -> salida aunque la señal sea HOLD
    feed.df = make_df([90.0, 90.0, 80.0])             # último cerrado = 90
    result = make_engine(feed, broker, store, const_decider(Action.HOLD)).run_cycle("BTC/USDT")
    assert result.action == "SELL"
    assert "stop-loss" in result.detail
    assert store.get_positions() == {}


def test_hold_without_position_does_nothing_but_snapshots():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    broker = LocalPaperBroker(cash=10000.0)
    store = Store(":memory:")
    result = make_engine(feed, broker, store, const_decider(Action.HOLD)).run_cycle("BTC/USDT")
    assert result.action == "HOLD"
    assert store.get_positions() == {}
    assert broker.cash() == 10000.0
    assert store.latest_equity() is not None
```

- [ ] **Step 3: Run para verificar que falla**

Run: `python -m pytest tests/test_engine_cycle.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.engine.runner'`.

- [ ] **Step 4: Implementar `bot/engine/runner.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from bot.broker.base import Broker
from bot.broker.models import Position
from bot.config import RiskParams, StrategyParams
from bot.data.feed import DataFeed, drop_forming_candle
from bot.models import Action, Signal
from bot.risk.manager import can_open, size_quantity, stop_loss_price, take_profit_price
from bot.store.db import Store
from bot.strategy.ema_rsi import evaluate


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CycleResult:
    symbol: str
    action: str
    detail: str


class Engine:
    def __init__(
        self,
        feed: DataFeed,
        broker: Broker,
        store: Store,
        strategy: StrategyParams,
        risk: RiskParams,
        timeframe: str = "1h",
        limit: int = 200,
        clock: Callable[[], str] = _utcnow,
        log: Callable[[str], None] = print,
        decider: Callable[[pd.DataFrame, StrategyParams], Signal] = evaluate,
    ) -> None:
        self.feed = feed
        self.broker = broker
        self.store = store
        self.strategy = strategy
        self.risk = risk
        self.timeframe = timeframe
        self.limit = limit
        self.clock = clock
        self.log = log
        self.decider = decider

    def _equity(self, prices: dict[str, float]) -> float:
        positions = self.store.get_positions()
        holdings_value = sum(
            p.quantity * prices.get(s, p.entry_price) for s, p in positions.items()
        )
        return self.broker.cash() + holdings_value

    def _snapshot(self, price_by_symbol: dict[str, float], ts: str) -> None:
        equity = self._equity(price_by_symbol)
        self.store.record_equity(ts, equity, self.broker.cash())

    def run_cycle(self, symbol: str) -> CycleResult:
        df = drop_forming_candle(self.feed.fetch_ohlcv(symbol, self.timeframe, self.limit))
        price = float(df["close"].iloc[-1])
        signal = self.decider(df, self.strategy)
        ts = self.clock()
        ind = signal.indicators
        self.store.record_decision(
            ts, symbol, signal.action.value, signal.reason,
            ind["ema_fast"], ind["ema_slow"], ind["rsi"],
        )

        positions = self.store.get_positions()
        pos = positions.get(symbol)

        # 1) Salida por riesgo (stop-loss / take-profit) antes que la señal.
        if pos is not None and (price <= pos.stop_loss or price >= pos.take_profit):
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(ts, fill)
            self.store.remove_position(symbol)
            reason = "stop-loss" if price <= pos.stop_loss else "take-profit"
            self.log(f"[{symbol}] SALIDA {reason} qty={fill.quantity:.6f} @ {fill.price:.2f}")
            self._snapshot({symbol: price}, ts)
            return CycleResult(symbol, "SELL", f"salida {reason} @ {fill.price:.2f}")

        # 2) Acción de la estrategia.
        detail = signal.reason
        if signal.action is Action.BUY and pos is None:
            equity = self._equity({symbol: price})
            if can_open(len(positions), self.risk):
                qty = size_quantity(equity, price, self.risk)
                if qty > 0:
                    fill = self.broker.buy(symbol, qty, price)
                    self.store.record_fill(ts, fill)
                    new_pos = Position(
                        symbol, fill.quantity, fill.price,
                        stop_loss_price(fill.price, self.risk),
                        take_profit_price(fill.price, self.risk),
                    )
                    self.store.upsert_position(new_pos, ts)
                    detail = f"compra qty={fill.quantity:.6f} @ {fill.price:.2f}"
                    self.log(f"[{symbol}] COMPRA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        elif signal.action is Action.SELL and pos is not None:
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(ts, fill)
            self.store.remove_position(symbol)
            detail = f"venta qty={fill.quantity:.6f} @ {fill.price:.2f}"
            self.log(f"[{symbol}] VENTA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        else:
            self.log(f"[{symbol}] {signal.action.value}: {signal.reason}")

        self._snapshot({symbol: price}, ts)
        return CycleResult(symbol, signal.action.value, detail)
```

- [ ] **Step 5: Run y verificar verde**

Run: `python -m pytest tests/test_engine_cycle.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add bot/engine/__init__.py bot/engine/runner.py tests/test_engine_cycle.py
git commit -m "feat: add engine run_cycle (decide, risk, execute, persist)"
```

---

### Task 9: `Engine.run_loop`

**Files:**
- Modify: `bot/engine/runner.py` (agregar `run_loop`)
- Test: `tests/test_engine_loop.py`

**Interfaces:**
- Produces: método `Engine.run_loop(symbols: list[str], interval_seconds: int, max_cycles: int | None = None, sleep: Callable[[float], None] = time.sleep) -> int` — corre `run_cycle` para cada símbolo por ciclo; aísla errores por símbolo (los loguea y sigue); duerme `interval_seconds` **entre** ciclos (no después del último); devuelve la cantidad de ciclos corridos. `max_cycles=None` significa indefinido; `sleep` se inyecta para testear.

- [ ] **Step 1: Escribir el test que falla** — `tests/test_engine_loop.py`:

```python
from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams, StrategyParams
from bot.engine.runner import Engine
from bot.models import Action, Signal
from bot.store.db import Store
from tests.conftest import make_df


class FakeFeed:
    def __init__(self, df):
        self.df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self.df


def hold_decider(df, params):
    return Signal(Action.HOLD, "test", {"ema_fast": 1.0, "ema_slow": 1.0, "rsi": 50.0})


def test_run_loop_runs_each_symbol_per_cycle_and_sleeps_between():
    feed = FakeFeed(make_df([float(x) for x in range(1, 61)]))
    store = Store(":memory:")
    sleeps = []
    engine = Engine(
        feed=feed, broker=LocalPaperBroker(cash=10000.0), store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        clock=lambda: "t", log=lambda m: None, decider=hold_decider,
    )
    cycles = engine.run_loop(
        ["BTC/USDT", "ETH/USDT"], interval_seconds=10, max_cycles=2,
        sleep=lambda s: sleeps.append(s),
    )
    assert cycles == 2
    # 2 símbolos * 2 ciclos = 4 decisiones
    assert len(store.recent_decisions(limit=100)) == 4
    # duerme una sola vez (entre los 2 ciclos, no después del último)
    assert sleeps == [10]


def test_run_loop_isolates_per_symbol_errors():
    store = Store(":memory:")

    class BoomFeed:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            if symbol == "BOOM/USDT":
                raise RuntimeError("feed caído")
            return make_df([float(x) for x in range(1, 61)])

    logs = []
    engine = Engine(
        feed=BoomFeed(), broker=LocalPaperBroker(cash=10000.0), store=store,
        strategy=StrategyParams(), risk=RiskParams(),
        clock=lambda: "t", log=lambda m: logs.append(m), decider=hold_decider,
    )
    cycles = engine.run_loop(
        ["BOOM/USDT", "BTC/USDT"], interval_seconds=1, max_cycles=1, sleep=lambda s: None
    )
    assert cycles == 1
    # el símbolo bueno igual decidió pese al error del otro
    actions = [d["symbol"] for d in store.recent_decisions(limit=100)]
    assert "BTC/USDT" in actions
    assert any("ERROR" in m for m in logs)
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_engine_loop.py -q`
Expected: FAIL con `AttributeError: 'Engine' object has no attribute 'run_loop'`.

- [ ] **Step 3: Implementar** — en `bot/engine/runner.py`: agregar `import time` al inicio (junto a los otros imports stdlib) y agregar el método `run_loop` a la clase `Engine` (debajo de `run_cycle`):

```python
    def run_loop(
        self,
        symbols: list[str],
        interval_seconds: int,
        max_cycles: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> int:
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            for symbol in symbols:
                try:
                    self.run_cycle(symbol)
                except Exception as exc:  # noqa: BLE001 - aislar fallos por símbolo
                    self.log(f"[{symbol}] ERROR: {exc}")
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            sleep(interval_seconds)
        return cycles
```

El import: la primera línea de imports stdlib del archivo debe quedar `import time` y `from datetime import datetime, timezone`.

- [ ] **Step 4: Run y verificar verde**

Run: `python -m pytest tests/test_engine_loop.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/engine/runner.py tests/test_engine_loop.py
git commit -m "feat: add engine run_loop with per-symbol error isolation"
```

---

### Task 10: CLI `run` / `status` + `build_broker` + corrida real

**Files:**
- Modify: `bot/cli.py`
- Test: `tests/test_cli_run.py`

**Interfaces:**
- Consumes: todo lo anterior + `bot.engine.runner.Engine`, `bot.store.db.Store`, `bot.broker.paper.LocalPaperBroker`, `bot.broker.okx_demo.OkxDemoBroker`.
- Produces:
  - `build_broker(config: Config) -> Broker` — `LocalPaperBroker` si `config.broker.kind == "paper"`; `OkxDemoBroker` (con claves de entorno `OKX_API_KEY/SECRET/PASSWORD`) si `"okx_demo"`.
  - Subcomando `run SYMBOL [--timeframe] [--exchange] [--loop] [--config]` — arma feed/broker/store/engine; corre un ciclo, o `run_loop` si `--loop`.
  - Subcomando `status [--config]` — abre el `Store` y muestra equity/caja, posiciones abiertas y las últimas decisiones.

- [ ] **Step 1: Escribir el test que falla** — `tests/test_cli_run.py`:

```python
from bot.cli import build_broker
from bot.config import BrokerParams, Config
from bot.broker.paper import LocalPaperBroker


def test_build_broker_paper_by_default():
    broker = build_broker(Config())
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 10000.0


def test_build_broker_paper_uses_config_cash():
    cfg = Config(broker=BrokerParams(kind="paper", paper_cash=2500.0))
    broker = build_broker(cfg)
    assert isinstance(broker, LocalPaperBroker)
    assert broker.cash() == 2500.0
```

- [ ] **Step 2: Run para verificar que falla**

Run: `python -m pytest tests/test_cli_run.py -q`
Expected: FAIL con `ImportError: cannot import name 'build_broker'`.

- [ ] **Step 3: Implementar** — reemplazar **todo** el contenido de `bot/cli.py` por:

```python
from __future__ import annotations

import argparse
import os

from bot.broker.base import Broker
from bot.broker.okx_demo import OkxDemoBroker
from bot.broker.paper import LocalPaperBroker
from bot.config import Config, load_config
from bot.data.feed import CcxtDataFeed, DataFeed, drop_forming_candle
from bot.engine.runner import Engine
from bot.models import Signal
from bot.store.db import Store
from bot.strategy.ema_rsi import evaluate


def run_decide(
    feed: DataFeed, config: Config, symbol: str, timeframe: str, limit: int = 200
) -> Signal:
    df = drop_forming_candle(feed.fetch_ohlcv(symbol, timeframe, limit))
    return evaluate(df, config.strategy)


def build_broker(config: Config) -> Broker:
    bp = config.broker
    if bp.kind == "okx_demo":
        return OkxDemoBroker(
            os.environ["OKX_API_KEY"],
            os.environ["OKX_API_SECRET"],
            os.environ["OKX_API_PASSWORD"],
        )
    return LocalPaperBroker(bp.paper_cash, bp.fee_rate, bp.slippage)


def _cmd_decide(args) -> int:
    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe
    feed = CcxtDataFeed(exchange)
    signal = run_decide(feed, config, args.symbol, timeframe, config.limit)
    print(f"[{args.symbol} · {timeframe} · {exchange}]")
    print(f"Decisión: {signal.action.value}")
    print(f"Motivo:   {signal.reason}")
    ind = signal.indicators
    print(
        f"EMA fast: {ind['ema_fast']:.2f}  "
        f"EMA slow: {ind['ema_slow']:.2f}  "
        f"RSI: {ind['rsi']:.1f}"
    )
    return 0


def _cmd_run(args) -> int:
    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe
    engine = Engine(
        feed=CcxtDataFeed(exchange),
        broker=build_broker(config),
        store=Store(config.db_path),
        strategy=config.strategy,
        risk=config.risk,
        timeframe=timeframe,
        limit=config.limit,
    )
    if args.loop:
        print(f"Loop cada {config.loop_interval_seconds}s · {config.broker.kind} · {exchange}")
        engine.run_loop([args.symbol], config.loop_interval_seconds)
    else:
        result = engine.run_cycle(args.symbol)
        print(f"[{result.symbol}] {result.action}: {result.detail}")
    return 0


def _cmd_status(args) -> int:
    config = load_config(args.config)
    store = Store(config.db_path)
    eq = store.latest_equity()
    if eq is None:
        print("Sin corridas todavía. Ejecutá: python -m bot run BTC/USDT")
        return 0
    equity, cash = eq
    print(f"Equity: {equity:.2f}  ·  Caja: {cash:.2f}")
    positions = store.get_positions()
    print(f"Posiciones abiertas: {len(positions)}")
    for sym, p in positions.items():
        print(
            f"  {sym}: qty={p.quantity:.6f} entrada={p.entry_price:.2f} "
            f"SL={p.stop_loss:.2f} TP={p.take_profit:.2f}"
        )
    print("Últimas decisiones:")
    for d in store.recent_decisions(limit=5):
        print(f"  {d['ts']} {d['symbol']} {d['action']} — {d['reason']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="Muestra la decisión (sin operar)")
    d.add_argument("symbol")
    d.add_argument("--timeframe", default=None)
    d.add_argument("--exchange", default=None)
    d.add_argument("--config", default="config.yaml")
    d.set_defaults(func=_cmd_decide)

    r = sub.add_parser("run", help="Corre un ciclo (o un loop con --loop) y opera en paper")
    r.add_argument("symbol")
    r.add_argument("--timeframe", default=None)
    r.add_argument("--exchange", default=None)
    r.add_argument("--loop", action="store_true")
    r.add_argument("--config", default="config.yaml")
    r.set_defaults(func=_cmd_run)

    s = sub.add_parser("status", help="Muestra equity, posiciones y últimas decisiones")
    s.add_argument("--config", default="config.yaml")
    s.set_defaults(func=_cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)
```

- [ ] **Step 4: Run y verificar verde**

Run: `python -m pytest tests/test_cli_run.py -q`
Expected: PASS (2 passed). Después la suite completa: `python -m pytest -q` (todo verde).

- [ ] **Step 5: Commit**

```bash
git add bot/cli.py tests/test_cli_run.py
git commit -m "feat: add run/status CLI and broker factory"
```

- [ ] **Step 6: Corrida manual con datos REALES (paper local)**

Con `config.yaml` en `broker.kind: paper`:

```bash
python -m bot run BTC/USDT --timeframe 1h
python -m bot status
```

Expected: `run` baja datos reales, decide sobre la vela cerrada, y si la señal es `BUY`/`SELL` ejecuta una orden simulada (o informa `HOLD`); persiste en `americo.sqlite`. `status` muestra equity, caja, posiciones abiertas y las últimas decisiones. Si OKX está geo-restringido, usá `--exchange kraken`. (La acción concreta depende del mercado; lo importante es que el ciclo completo corra de punta a punta sobre datos reales y deje estado persistido.)

---

## Resultado de la Fase 1

Al completar las 10 tasks, AMÉRICO **opera en paper de punta a punta**: decide sobre la última vela cerrada, dimensiona la posición por riesgo (1% por trade, con stop-loss/take-profit y tope de exposición), ejecuta órdenes simuladas vía `LocalPaperBroker` (o `OkxDemoBroker` cambiando `broker.kind` + claves de entorno), persiste decisiones/fills/posiciones/equity en SQLite, y corre un ciclo único o un loop continuo. Queda listo para el plan siguiente (Fase 3): la **API (FastAPI) + el panel web** que leen ese estado y lo muestran en vivo.
