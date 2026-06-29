# Núcleo de decisión (Fase 0) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el núcleo de decisión del bot: a partir de datos de mercado **reales** (CCXT público), calcular indicadores (EMA/RSI), evaluar una estrategia de reglas y emitir una decisión `BUY/SELL/HOLD` con su razonamiento, ejecutable desde la línea de comandos.

**Architecture:** Paquete Python `bot/` con piezas separadas por responsabilidad e interfaces (`DataFeed`, estrategia pura). El flujo es `DataFeed → indicadores → compute_features → decide → Signal`. La lógica de decisión es una **función pura** sobre valores numéricos (testeable sin red ni cálculo de EMA a mano); la obtención de datos vive detrás de una interfaz con una implementación real (CCXT) y un doble de test.

**Tech Stack:** Python 3.11+, `ccxt` (datos de mercado), `pandas` (series/indicadores), `PyYAML` (config), `pytest` (tests). Sin `pandas-ta`/`vectorbt` todavía (llegan en planes posteriores).

## Global Constraints

- **Python:** `>=3.11`.
- **Dependencias (pisos de versión, exactos):** `ccxt>=4.4`, `pandas>=2.2`, `PyYAML>=6.0`, `pytest>=8.0`.
- **Tests unitarios sin red:** ningún test puede llamar a un exchange real. El acceso a red se prueba solo en el paso manual de la Task 7.
- **Indicadores propios:** EMA y RSI se implementan a mano sobre pandas (no se agrega `pandas-ta`).
- **La lógica de decisión es una función pura** `decide(Features, StrategyParams) -> Signal` (sin I/O).
- **Commits frecuentes**, uno por task. Cada mensaje de commit termina con el trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- **Paquete importable desde la raíz del repo** (`pyproject.toml` fija `pythonpath = ["."]`); todos los comandos se corren desde la raíz `trading/`.
- **Idioma:** identificadores y mensajes de commit en inglés; textos visibles al usuario (motivos de la señal, salida de CLI) en español.

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `pyproject.toml` | Metadata + config de pytest (`pythonpath`, `testpaths`) |
| `requirements.txt` | Dependencias con pisos de versión |
| `.gitignore` | Ignora venv, caches, `.env`, DBs |
| `config.yaml` | Config por defecto (exchange, timeframe, símbolos, parámetros de estrategia) |
| `.env.example` | Plantilla de variables de entorno (vacía en Fase 0) |
| `bot/__init__.py` | Marca el paquete |
| `bot/models.py` | `Action` (enum), `Signal` (dataclass) |
| `bot/indicators.py` | `ema()`, `rsi()` |
| `bot/config.py` | `StrategyParams`, `Config`, `load_config()` |
| `bot/data/feed.py` | `OHLCV_COLUMNS`, `ohlcv_to_df()`, `DataFeed` (Protocol), `CcxtDataFeed` |
| `bot/strategy/ema_rsi.py` | `Features`, `compute_features()`, `decide()`, `evaluate()` |
| `bot/cli.py` | `run_decide()`, `main()` |
| `bot/__main__.py` | Permite `python -m bot` |
| `tests/...` | Tests por módulo + `conftest.py` con fixtures |

---

### Task 1: Scaffolding del proyecto

**Files:**
- Create: `requirements.txt`, `pyproject.toml`, `.gitignore`, `config.yaml`, `.env.example`
- Create: `bot/__init__.py`, `bot/data/__init__.py`, `bot/strategy/__init__.py`, `tests/__init__.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nada.
- Produces: estructura de paquete importable (`import bot`), `pytest` corriendo en verde.

- [ ] **Step 1: Crear la rama de trabajo**

```bash
git checkout -b feat/nucleo-decision
```

- [ ] **Step 2: Crear `requirements.txt`**

```
ccxt>=4.4
pandas>=2.2
PyYAML>=6.0
pytest>=8.0
```

- [ ] **Step 3: Crear `pyproject.toml`**

```toml
[project]
name = "americo-bot"
version = "0.1.0"
description = "Bot de trading cripto (paper) con decisión por reglas"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Crear `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
config-private.yaml
*.sqlite
.pytest_cache/
```

- [ ] **Step 5: Crear `config.yaml`**

```yaml
exchange: okx
timeframe: "1h"
symbols:
  - BTC/USDT
  - ETH/USDT
strategy:
  fast: 20
  slow: 50
  rsi_period: 14
  rsi_oversold: 35
  rsi_overbought: 70
```

- [ ] **Step 6: Crear `.env.example`**

```
# Solo se usa en fases posteriores (ejecución en OKX Demo / real).
# OKX_API_KEY=
# OKX_API_SECRET=
# OKX_API_PASSWORD=
# ANTHROPIC_API_KEY=
```

- [ ] **Step 7: Crear los `__init__.py` vacíos**

Crear archivos vacíos: `bot/__init__.py`, `bot/data/__init__.py`, `bot/strategy/__init__.py`, `tests/__init__.py`.

- [ ] **Step 8: Crear el venv e instalar dependencias**

```bash
python -m venv .venv
```

Activar el entorno (PowerShell: `.\.venv\Scripts\Activate.ps1`; bash/Git Bash: `source .venv/Scripts/activate`), y luego:

```bash
python -m pip install -r requirements.txt
```

Expected: instala ccxt, pandas, PyYAML, pytest sin errores.

- [ ] **Step 9: Escribir el smoke test**

`tests/test_smoke.py`:

```python
import bot


def test_package_imports():
    assert bot is not None
```

- [ ] **Step 10: Correr el smoke test**

Run: `python -m pytest -q`
Expected: PASS (1 passed).

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "chore: scaffold americo-bot package and tooling"
```

---

### Task 2: Modelos de dominio (`Action`, `Signal`)

**Files:**
- Create: `bot/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `class Action(str, Enum)` con miembros `BUY`, `SELL`, `HOLD`.
  - `@dataclass(frozen=True) class Signal` con campos `action: Action`, `reason: str`, `indicators: dict[str, float]` (default `{}`).

- [ ] **Step 1: Escribir el test que falla**

`tests/test_models.py`:

```python
from bot.models import Action, Signal


def test_signal_has_defaults():
    s = Signal(Action.HOLD, "sin señal")
    assert s.action is Action.HOLD
    assert s.reason == "sin señal"
    assert s.indicators == {}


def test_action_values():
    assert Action.BUY.value == "BUY"
    assert {a.value for a in Action} == {"BUY", "SELL", "HOLD"}
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_models.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.models'`.

- [ ] **Step 3: Implementación mínima**

`bot/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    action: Action
    reason: str
    indicators: dict[str, float] = field(default_factory=dict)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_models.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/models.py tests/test_models.py
git commit -m "feat: add Action and Signal domain models"
```

---

### Task 3: Indicadores (`ema`, `rsi`)

**Files:**
- Create: `bot/indicators.py`
- Test: `tests/test_indicators.py`

**Interfaces:**
- Consumes: `pandas`.
- Produces:
  - `ema(series: pd.Series, period: int) -> pd.Series` (EMA con `adjust=False`).
  - `rsi(series: pd.Series, period: int = 14) -> pd.Series` (RSI tipo Wilder; serie estrictamente creciente → 100, decreciente → 0).

- [ ] **Step 1: Escribir el test que falla**

`tests/test_indicators.py`:

```python
import pandas as pd

from bot.indicators import ema, rsi


def test_ema_of_constant_is_constant():
    s = pd.Series([5.0, 5.0, 5.0, 5.0])
    assert ema(s, 2).iloc[-1] == 5.0


def test_ema_known_value():
    # span=2 -> alpha=2/3; [1,2] con adjust=False -> 5/3
    s = pd.Series([1.0, 2.0])
    assert abs(ema(s, 2).iloc[-1] - (5 / 3)) < 1e-9


def test_rsi_all_gains_is_100():
    s = pd.Series([float(x) for x in range(1, 21)])
    assert rsi(s, 14).iloc[-1] == 100.0


def test_rsi_all_losses_is_0():
    s = pd.Series([float(x) for x in range(20, 0, -1)])
    assert rsi(s, 14).iloc[-1] == 0.0
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_indicators.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.indicators'`.

- [ ] **Step 3: Implementación mínima**

`bot/indicators.py`:

```python
from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_indicators.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/indicators.py tests/test_indicators.py
git commit -m "feat: add ema and rsi indicators"
```

---

### Task 4: Configuración (`StrategyParams`, `Config`, `load_config`)

**Files:**
- Create: `bot/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `PyYAML`.
- Produces:
  - `@dataclass class StrategyParams` con `fast:int=20`, `slow:int=50`, `rsi_period:int=14`, `rsi_oversold:float=35.0`, `rsi_overbought:float=70.0`.
  - `@dataclass class Config` con `exchange:str="okx"`, `timeframe:str="1h"`, `symbols:list[str]=["BTC/USDT"]`, `strategy:StrategyParams`.
  - `load_config(path: str | Path) -> Config`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_config.py`:

```python
from bot.config import Config, StrategyParams, load_config


def test_load_config_reads_values(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "exchange: kraken\n"
        "timeframe: '4h'\n"
        "symbols:\n"
        "  - ETH/USDT\n"
        "strategy:\n"
        "  fast: 9\n"
        "  slow: 21\n",
        encoding="utf-8",
    )
    c = load_config(p)
    assert c.exchange == "kraken"
    assert c.timeframe == "4h"
    assert c.symbols == ["ETH/USDT"]
    assert c.strategy.fast == 9
    assert c.strategy.slow == 21
    assert c.strategy.rsi_period == 14  # default conservado


def test_load_config_uses_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("{}", encoding="utf-8")
    c = load_config(p)
    assert c == Config()
    assert c.strategy == StrategyParams()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.config'`.

- [ ] **Step 3: Implementación mínima**

`bot/config.py`:

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
class Config:
    exchange: str = "okx"
    timeframe: str = "1h"
    symbols: list[str] = field(default_factory=lambda: ["BTC/USDT"])
    strategy: StrategyParams = field(default_factory=StrategyParams)


def load_config(path: str | Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    strat = data.get("strategy") or {}
    return Config(
        exchange=data.get("exchange", "okx"),
        timeframe=data.get("timeframe", "1h"),
        symbols=data.get("symbols", ["BTC/USDT"]),
        strategy=StrategyParams(
            fast=strat.get("fast", 20),
            slow=strat.get("slow", 50),
            rsi_period=strat.get("rsi_period", 14),
            rsi_oversold=strat.get("rsi_oversold", 35.0),
            rsi_overbought=strat.get("rsi_overbought", 70.0),
        ),
    )
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/config.py tests/test_config.py
git commit -m "feat: add config loading with strategy params"
```

---

### Task 5: DataFeed (datos reales por CCXT + conversión a DataFrame)

**Files:**
- Create: `bot/data/feed.py`
- Test: `tests/test_feed.py`

**Interfaces:**
- Consumes: `pandas`, `ccxt` (solo en `CcxtDataFeed`).
- Produces:
  - `OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]`.
  - `ohlcv_to_df(rows: list[list[float]]) -> pd.DataFrame` (convierte la salida cruda de CCXT; `timestamp` a datetime UTC).
  - `class DataFeed(Protocol)` con `fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame`.
  - `class CcxtDataFeed` con `__init__(self, exchange_id: str = "okx")` y `fetch_ohlcv(...)`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_feed.py`:

```python
from bot.data.feed import OHLCV_COLUMNS, ohlcv_to_df


def test_ohlcv_to_df_shapes_columns_and_time():
    rows = [
        [1700000000000, 1.0, 2.0, 0.5, 1.5, 10.0],
        [1700003600000, 1.5, 2.5, 1.0, 2.0, 12.0],
    ]
    df = ohlcv_to_df(rows)
    assert list(df.columns) == OHLCV_COLUMNS
    assert df["close"].iloc[-1] == 2.0
    assert str(df["timestamp"].dtype).startswith("datetime64")
    assert len(df) == 2
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_feed.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.data.feed'`.

- [ ] **Step 3: Implementación mínima**

`bot/data/feed.py`:

```python
from __future__ import annotations

from typing import Protocol

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def ohlcv_to_df(rows: list[list[float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


class DataFeed(Protocol):
    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> pd.DataFrame: ...


class CcxtDataFeed:
    def __init__(self, exchange_id: str = "okx") -> None:
        import ccxt

        self._exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 200
    ) -> pd.DataFrame:
        rows = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv_to_df(rows)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_feed.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add bot/data/feed.py tests/test_feed.py
git commit -m "feat: add DataFeed protocol and CCXT implementation"
```

---

### Task 6: Estrategia (`Features`, `compute_features`, `decide`, `evaluate`)

**Files:**
- Create: `bot/strategy/ema_rsi.py`
- Create: `tests/conftest.py`
- Test: `tests/test_strategy.py`

**Interfaces:**
- Consumes: `bot.config.StrategyParams`, `bot.indicators.ema`, `bot.indicators.rsi`, `bot.models.Action`, `bot.models.Signal`, `pandas`.
- Produces:
  - `@dataclass class Features` con `ema_fast`, `ema_slow`, `ema_fast_prev`, `ema_slow_prev`, `rsi` (todos `float`).
  - `compute_features(df: pd.DataFrame, params: StrategyParams) -> Features`.
  - `decide(f: Features, params: StrategyParams) -> Signal` (función pura).
  - `evaluate(df: pd.DataFrame, params: StrategyParams) -> Signal`.
- Fixture: `uptrend_df` (DataFrame con cierres `1..80`) en `tests/conftest.py`.

- [ ] **Step 1: Crear las fixtures de test**

`tests/conftest.py`:

```python
import pandas as pd
import pytest


def make_df(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * n,
        }
    )


@pytest.fixture
def uptrend_df() -> pd.DataFrame:
    return make_df([float(x) for x in range(1, 81)])
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_strategy.py`:

```python
from bot.config import StrategyParams
from bot.models import Action
from bot.strategy.ema_rsi import Features, compute_features, decide, evaluate

P = StrategyParams()


def test_decide_buy_on_bullish_cross():
    f = Features(ema_fast=11, ema_slow=10, ema_fast_prev=9, ema_slow_prev=10, rsi=40)
    assert decide(f, P).action is Action.BUY


def test_decide_sell_on_bearish_cross():
    f = Features(ema_fast=9, ema_slow=10, ema_fast_prev=11, ema_slow_prev=10, rsi=50)
    assert decide(f, P).action is Action.SELL


def test_decide_sell_on_overbought():
    f = Features(ema_fast=10, ema_slow=10, ema_fast_prev=10, ema_slow_prev=10, rsi=75)
    assert decide(f, P).action is Action.SELL


def test_decide_hold_when_neutral():
    f = Features(ema_fast=10.5, ema_slow=10.0, ema_fast_prev=10.4, ema_slow_prev=10.0, rsi=55)
    assert decide(f, P).action is Action.HOLD


def test_compute_features_uptrend(uptrend_df):
    feats = compute_features(uptrend_df, P)
    assert feats.ema_fast > feats.ema_slow
    assert feats.rsi > 50


def test_evaluate_returns_signal(uptrend_df):
    sig = evaluate(uptrend_df, P)
    assert sig.action in (Action.BUY, Action.SELL, Action.HOLD)
    assert set(sig.indicators) == {"ema_fast", "ema_slow", "rsi"}
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_strategy.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.strategy.ema_rsi'`.

- [ ] **Step 4: Implementación mínima**

`bot/strategy/ema_rsi.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bot.config import StrategyParams
from bot.indicators import ema, rsi
from bot.models import Action, Signal


@dataclass
class Features:
    ema_fast: float
    ema_slow: float
    ema_fast_prev: float
    ema_slow_prev: float
    rsi: float


def compute_features(df: pd.DataFrame, params: StrategyParams) -> Features:
    close = df["close"]
    ef = ema(close, params.fast)
    es = ema(close, params.slow)
    r = rsi(close, params.rsi_period)
    return Features(
        ema_fast=float(ef.iloc[-1]),
        ema_slow=float(es.iloc[-1]),
        ema_fast_prev=float(ef.iloc[-2]),
        ema_slow_prev=float(es.iloc[-2]),
        rsi=float(r.iloc[-1]),
    )


def decide(f: Features, params: StrategyParams) -> Signal:
    indicators = {"ema_fast": f.ema_fast, "ema_slow": f.ema_slow, "rsi": f.rsi}
    cross_up = f.ema_fast_prev <= f.ema_slow_prev and f.ema_fast > f.ema_slow
    cross_down = f.ema_fast_prev >= f.ema_slow_prev and f.ema_fast < f.ema_slow

    if cross_up and f.rsi < params.rsi_overbought:
        reason = f"EMA{params.fast} cruzó por encima de EMA{params.slow} (RSI {f.rsi:.0f})"
        return Signal(Action.BUY, reason, indicators)

    if cross_down or f.rsi >= params.rsi_overbought:
        reason = (
            "RSI en sobrecompra"
            if f.rsi >= params.rsi_overbought
            else f"EMA{params.fast} cruzó por debajo de EMA{params.slow}"
        )
        return Signal(Action.SELL, reason, indicators)

    return Signal(Action.HOLD, "Sin cruce de EMAs ni señal de RSI", indicators)


def evaluate(df: pd.DataFrame, params: StrategyParams) -> Signal:
    return decide(compute_features(df, params), params)
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_strategy.py -q`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add bot/strategy/ema_rsi.py tests/conftest.py tests/test_strategy.py
git commit -m "feat: add ema/rsi strategy with pure decide function"
```

---

### Task 7: CLI (`run_decide`, `main`) + verificación con datos reales

**Files:**
- Create: `bot/cli.py`
- Create: `bot/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `bot.config.Config`, `bot.config.load_config`, `bot.data.feed.DataFeed`, `bot.data.feed.CcxtDataFeed`, `bot.models.Signal`, `bot.strategy.ema_rsi.evaluate`.
- Produces:
  - `run_decide(feed: DataFeed, config: Config, symbol: str, timeframe: str, limit: int = 200) -> Signal`.
  - `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_cli.py` (usa un doble de `DataFeed` en memoria; sin red):

```python
from bot.cli import run_decide
from bot.config import Config
from bot.models import Action


class FakeFeed:
    def __init__(self, df):
        self._df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self._df


def test_run_decide_returns_signal_from_feed(uptrend_df):
    sig = run_decide(FakeFeed(uptrend_df), Config(), "BTC/USDT", "1h")
    assert isinstance(sig.action, Action)
    assert set(sig.indicators) == {"ema_fast", "ema_slow", "rsi"}
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'bot.cli'`.

- [ ] **Step 3: Implementación mínima**

`bot/cli.py`:

```python
from __future__ import annotations

import argparse

from bot.config import Config, load_config
from bot.data.feed import CcxtDataFeed, DataFeed
from bot.models import Signal
from bot.strategy.ema_rsi import evaluate


def run_decide(
    feed: DataFeed, config: Config, symbol: str, timeframe: str, limit: int = 200
) -> Signal:
    df = feed.fetch_ohlcv(symbol, timeframe, limit)
    return evaluate(df, config.strategy)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)
    decide_cmd = sub.add_parser("decide", help="Evalúa la estrategia y muestra la decisión")
    decide_cmd.add_argument("symbol", help="Par, ej. BTC/USDT")
    decide_cmd.add_argument("--timeframe", default=None)
    decide_cmd.add_argument("--exchange", default=None)
    decide_cmd.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe

    feed = CcxtDataFeed(exchange)
    signal = run_decide(feed, config, args.symbol, timeframe)

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
```

`bot/__main__.py`:

```python
import sys

from bot.cli import main

sys.exit(main())
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Correr toda la suite**

Run: `python -m pytest -q`
Expected: PASS (todos los tests; 17 passed).

- [ ] **Step 6: Verificación manual con datos REALES (red)**

Run: `python -m bot decide BTC/USDT --timeframe 1h`
Expected: imprime algo como:

```
[BTC/USDT · 1h · okx]
Decisión: HOLD
Motivo:   Sin cruce de EMAs ni señal de RSI
EMA fast: 67431.05  EMA slow: 66980.12  RSI: 54.3
```

Si OKX está geo-restringido o falla la red desde tu IP, reintentá con otro exchange público:
`python -m bot decide BTC/USDT --timeframe 1h --exchange kraken`
(La acción concreta dependerá del mercado en ese momento; lo importante es que obtenga datos reales y emita una decisión con su razonamiento.)

- [ ] **Step 7: Commit**

```bash
git add bot/cli.py bot/__main__.py tests/test_cli.py
git commit -m "feat: add decide CLI over real CCXT data"
```

---

## Resultado de la Fase 0

Al completar las 7 tasks tenés un núcleo de decisión funcionando y testeado: `python -m bot decide BTC/USDT --timeframe 1h` obtiene datos **reales** del exchange, calcula EMA/RSI, evalúa la estrategia de reglas y muestra `BUY/SELL/HOLD` con su razonamiento. El `timeframe` es configurable (diario e intradía con el mismo código), la obtención de datos está detrás de la interfaz `DataFeed`, y la lógica de decisión es una función pura testeada — base lista para los planes siguientes (broker paper sobre OKX Demo, gestión de riesgo, scheduler 24/7, persistencia, capa IA y panel).
