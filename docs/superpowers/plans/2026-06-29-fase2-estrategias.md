# Fase 2 — Estrategias pluggables · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear un registro de estrategias pluggables con interfaz uniforme `decide(df, params: dict) -> Signal`, adaptar la estrategia EMA/RSI existente, e implementar cuatro estrategias nuevas (MACD, Bollinger, Breakout Donchian, Price Action), todas como funciones puras con TDD.

**Architecture:** Cada estrategia es una función pura `(pandas.DataFrame, dict) -> Signal` que decide sobre la última vela del df (el motor ya descarta la vela en formación antes de llamar). Un módulo `registry` mapea nombre → función. Los indicadores reutilizables (MACD, Bandas de Bollinger) se agregan a `bot/indicators.py`; Donchian y los patrones de vela se calculan dentro de su estrategia.

**Tech Stack:** Python 3.11, pandas, pytest. Sin dependencias nuevas.

## Global Constraints

- Interfaz uniforme: `decide(df: pd.DataFrame, params: dict) -> Signal`. `df` tiene columnas `timestamp, open, high, low, close, volume` y NO incluye la vela en formación (el motor la descarta). La decisión es sobre `df.iloc[-1]` (última vela cerrada), comparando con `df.iloc[-2]` para cruces.
- `Signal(action: Action, reason: str, indicators: dict[str, float])` de `bot/models.py`. `Action.BUY/SELL/HOLD`.
- Funciones PURAS: sin estado, sin IO, sin red. Determinísticas.
- Reusar `bot/indicators.py` (`ema(series, period)`, `rsi(series, period)`).
- NO tocar el motor (`bot/engine/runner.py`) en esta fase: el cableado por cuenta es la Fase 3. El motor sigue usando `evaluate` de `ema_rsi` para la cuenta `default`.
- TDD con velas sintéticas. Tests con `.venv/Scripts/python.exe -m pytest -q`. Commits frecuentes con `git add` de archivos específicos (NUNCA `git add -A`).
- No tocar `web/`, `docker-compose.yml`, `config.docker.yaml`.
- **Datos de test ilustrativos:** las velas sintéticas de cada test buscan gatillar la señal afirmada en la ÚLTIMA vela. Si al correr el test la señal no se dispara (los indicadores con ventanas móviles son sensibles a los valores exactos), **ajustá los valores de las velas** —no la lógica de la estrategia— hasta que pase. El contrato de cada estrategia son las REGLAS descritas en su bloque *Interfaces*; los números de las velas son medio para probarlas.

---

### Task 1: Registro de estrategias + adaptación de EMA/RSI

**Files:**
- Create: `bot/strategy/base.py` (tipo `StrategyFn`)
- Create: `bot/strategy/registry.py` (`STRATEGIES`, `get_strategy`, `available`)
- Test: `tests/test_strategy_registry.py`

**Interfaces:**
- Consumes: `evaluate(df, StrategyParams)` de `bot/strategy/ema_rsi.py`; `StrategyParams` de `bot/config.py`; `Signal` de `bot/models.py`.
- Produces:
  - `StrategyFn = Callable[[pd.DataFrame, dict], Signal]` (en `base.py`).
  - `decide_ema_rsi(df, params: dict) -> Signal` (en `registry.py`): arma `StrategyParams` desde el dict (defaults fast=20, slow=50, rsi_period=14, rsi_oversold=35.0, rsi_overbought=70.0) y delega en `evaluate`.
  - `STRATEGIES: dict[str, StrategyFn]` (en `registry.py`) — arranca con `{"ema_rsi": decide_ema_rsi}`.
  - `get_strategy(name) -> StrategyFn` (KeyError con mensaje si no existe).
  - `available() -> list[str]` (nombres ordenados).

- [ ] **Step 1: Test que falla**

```python
# tests/test_strategy_registry.py
from __future__ import annotations

import pandas as pd
import pytest

from bot.models import Action
from bot.strategy.registry import available, get_strategy


def _crossover_df():
    # EMA rápida cruza por encima de la lenta en la última vela; RSI en zona media.
    closes = [10, 10, 10, 10, 10, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_registry_has_ema_rsi():
    assert "ema_rsi" in available()


def test_unknown_strategy_raises():
    with pytest.raises(KeyError):
        get_strategy("noexiste")


def test_ema_rsi_buys_on_crossover():
    fn = get_strategy("ema_rsi")
    sig = fn(_crossover_df(), {"fast": 2, "slow": 4, "rsi_period": 3, "rsi_overbought": 90})
    assert sig.action is Action.BUY
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_registry.py -q`
Expected: FAIL (`ModuleNotFoundError: bot.strategy.registry`).

- [ ] **Step 3: Crear `base.py` y `registry.py`**

```python
# bot/strategy/base.py
from __future__ import annotations

from typing import Callable

import pandas as pd

from bot.models import Signal

StrategyFn = Callable[[pd.DataFrame, dict], Signal]
```

```python
# bot/strategy/registry.py
from __future__ import annotations

from bot.config import StrategyParams
from bot.models import Signal
from bot.strategy.base import StrategyFn
from bot.strategy.ema_rsi import evaluate


def decide_ema_rsi(df, params: dict) -> Signal:
    sp = StrategyParams(
        fast=params.get("fast", 20),
        slow=params.get("slow", 50),
        rsi_period=params.get("rsi_period", 14),
        rsi_oversold=params.get("rsi_oversold", 35.0),
        rsi_overbought=params.get("rsi_overbought", 70.0),
    )
    return evaluate(df, sp)


STRATEGIES: dict[str, StrategyFn] = {
    "ema_rsi": decide_ema_rsi,
}


def get_strategy(name: str) -> StrategyFn:
    if name not in STRATEGIES:
        raise KeyError(
            f"Estrategia desconocida: {name!r}. Disponibles: {sorted(STRATEGIES)}"
        )
    return STRATEGIES[name]


def available() -> list[str]:
    return sorted(STRATEGIES)
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_registry.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add bot/strategy/base.py bot/strategy/registry.py tests/test_strategy_registry.py
git commit -m "feat(strategy): registro pluggable + adaptacion de ema_rsi"
```

---

### Task 2: Estrategia MACD

**Files:**
- Modify: `bot/indicators.py` (agregar `macd`)
- Create: `bot/strategy/macd.py`
- Modify: `bot/strategy/registry.py` (registrar `"macd"`)
- Test: `tests/test_indicators_macd.py`, `tests/test_strategy_macd.py`

**Interfaces:**
- Produces:
  - `macd(series, fast=12, slow=26, signal=9) -> tuple[pd.Series, pd.Series, pd.Series]` → `(macd_line, signal_line, hist)` donde `macd_line = ema(fast) - ema(slow)`, `signal_line = ema(macd_line, signal)`, `hist = macd_line - signal_line`.
  - `decide_macd(df, params: dict) -> Signal`: params `{fast, slow, signal}` (defaults 12, 26, 9). BUY cuando el histograma cruza de ≤0 a >0; SELL cuando cruza de ≥0 a <0; si no, HOLD. `indicators = {"macd": ..., "signal": ..., "hist": ...}`.

- [ ] **Step 1: Tests que fallan**

```python
# tests/test_indicators_macd.py
from __future__ import annotations

import pandas as pd

from bot.indicators import macd


def test_macd_shapes_and_relation():
    s = pd.Series([float(i) for i in range(40)])
    line, signal, hist = macd(s, fast=3, slow=6, signal=2)
    assert len(line) == len(signal) == len(hist) == 40
    # hist == line - signal (donde no hay NaN)
    assert abs((hist - (line - signal)).dropna().abs().max()) < 1e-9
```

```python
# tests/test_strategy_macd.py
from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.macd import decide_macd


def _df(closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_macd_buys_when_hist_turns_positive():
    # Baja sostenida y luego sube fuerte: el histograma pasa de negativo a positivo.
    closes = [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 12, 14, 16, 18, 20]
    sig = decide_macd(_df(closes), {"fast": 3, "slow": 6, "signal": 2})
    assert sig.action is Action.BUY


def test_macd_sells_when_hist_turns_negative():
    closes = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 18, 16, 14, 12, 10]
    sig = decide_macd(_df(closes), {"fast": 3, "slow": 6, "signal": 2})
    assert sig.action is Action.SELL
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_indicators_macd.py tests/test_strategy_macd.py -q`
Expected: FAIL (`macd` y `bot.strategy.macd` no existen).

- [ ] **Step 3: Implementar el indicador**

Agregar a `bot/indicators.py`:
```python
def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist
```

- [ ] **Step 4: Implementar la estrategia**

```python
# bot/strategy/macd.py
from __future__ import annotations

import pandas as pd

from bot.indicators import macd
from bot.models import Action, Signal


def decide_macd(df: pd.DataFrame, params: dict) -> Signal:
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal_p = params.get("signal", 9)
    line, signal_line, hist = macd(df["close"], fast, slow, signal_p)
    ind = {
        "macd": float(line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "hist": float(hist.iloc[-1]),
    }
    prev, curr = float(hist.iloc[-2]), float(hist.iloc[-1])
    if prev <= 0 < curr:
        return Signal(Action.BUY, f"MACD cruzó al alza (hist {curr:.4f})", ind)
    if prev >= 0 > curr:
        return Signal(Action.SELL, f"MACD cruzó a la baja (hist {curr:.4f})", ind)
    return Signal(Action.HOLD, "MACD sin cruce", ind)
```

- [ ] **Step 5: Registrar en `registry.py`**

En `bot/strategy/registry.py`: agregar `from bot.strategy.macd import decide_macd` con los otros imports, y agregar `"macd": decide_macd,` al dict `STRATEGIES`.

- [ ] **Step 6: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_indicators_macd.py tests/test_strategy_macd.py tests/test_strategy_registry.py -q` → PASS

- [ ] **Step 7: Commit**

```bash
git add bot/indicators.py bot/strategy/macd.py bot/strategy/registry.py tests/test_indicators_macd.py tests/test_strategy_macd.py
git commit -m "feat(strategy): MACD (cruce de histograma)"
```

---

### Task 3: Estrategia Bollinger (reversión a la media)

**Files:**
- Modify: `bot/indicators.py` (agregar `bollinger`)
- Create: `bot/strategy/bollinger.py`
- Modify: `bot/strategy/registry.py` (registrar `"bollinger"`)
- Test: `tests/test_indicators_bollinger.py`, `tests/test_strategy_bollinger.py`

**Interfaces:**
- Produces:
  - `bollinger(series, period=20, num_std=2.0) -> tuple[pd.Series, pd.Series, pd.Series]` → `(mid, upper, lower)` con `mid = SMA(period)`, `std = rolling std(period, ddof=0)`, `upper = mid + num_std*std`, `lower = mid - num_std*std`.
  - `decide_bollinger(df, params: dict) -> Signal`: params `{period, num_std}` (defaults 20, 2.0). Usa la banda PREVIA (`lower.shift(1)`/`upper.shift(1)`, que no incluye la vela actual, evitando que la banda "persiga" al pinchazo). BUY cuando la vela previa rompió por debajo de su banda anterior y la actual recupera (`close[-2] < lower.shift(1)[-2]` y `close[-1] > close[-2]`); SELL simétrico con la banda superior (`close[-2] > upper.shift(1)[-2]` y `close[-1] < close[-2]`); si no, HOLD. `indicators = {"bb_mid", "bb_upper", "bb_lower"}`.

- [ ] **Step 1: Tests que fallan**

```python
# tests/test_indicators_bollinger.py
from __future__ import annotations

import pandas as pd

from bot.indicators import bollinger


def test_bollinger_bands_ordered():
    s = pd.Series([10.0, 11, 9, 12, 8, 13, 7, 14, 6, 15, 5, 16])
    mid, upper, lower = bollinger(s, period=4, num_std=2.0)
    tail = slice(4, None)
    assert (upper[tail] >= mid[tail]).all()
    assert (mid[tail] >= lower[tail]).all()
```

```python
# tests/test_strategy_bollinger.py
from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.bollinger import decide_bollinger


def _df(closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_bollinger_buys_on_reentry_from_below():
    # Estable en 100, un pinchazo abajo (95) y reentra (100): rebote de banda inferior.
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 95, 100]
    sig = decide_bollinger(_df(closes), {"period": 5, "num_std": 2.0})
    assert sig.action is Action.BUY


def test_bollinger_sells_on_reentry_from_above():
    closes = [100, 100, 100, 100, 100, 100, 100, 100, 105, 100]
    sig = decide_bollinger(_df(closes), {"period": 5, "num_std": 2.0})
    assert sig.action is Action.SELL
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/Scripts/python.exe -m pytest tests/test_indicators_bollinger.py tests/test_strategy_bollinger.py -q`
Expected: FAIL (no existen).

- [ ] **Step 3: Implementar el indicador**

Agregar a `bot/indicators.py`:
```python
def bollinger(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower
```

- [ ] **Step 4: Implementar la estrategia**

```python
# bot/strategy/bollinger.py
from __future__ import annotations

import math

import pandas as pd

from bot.indicators import bollinger
from bot.models import Action, Signal


def decide_bollinger(df: pd.DataFrame, params: dict) -> Signal:
    period = params.get("period", 20)
    num_std = params.get("num_std", 2.0)
    mid, upper, lower = bollinger(df["close"], period, num_std)
    lower_ref = lower.shift(1)  # banda PREVIA (no incluye la vela que pinchó)
    upper_ref = upper.shift(1)
    ind = {
        "bb_mid": float(mid.iloc[-1]),
        "bb_upper": float(upper.iloc[-1]),
        "bb_lower": float(lower.iloc[-1]),
    }
    c_prev, c_now = float(df["close"].iloc[-2]), float(df["close"].iloc[-1])
    lo_ref = float(lower_ref.iloc[-2])
    up_ref = float(upper_ref.iloc[-2])
    if math.isnan(lo_ref) or math.isnan(up_ref):
        return Signal(Action.HOLD, "Bollinger sin datos suficientes", ind)
    if c_prev < lo_ref and c_now > c_prev:
        return Signal(Action.BUY, "Rebote desde la banda inferior", ind)
    if c_prev > up_ref and c_now < c_prev:
        return Signal(Action.SELL, "Reversión desde la banda superior", ind)
    return Signal(Action.HOLD, "Dentro de las bandas", ind)
```

- [ ] **Step 5: Registrar en `registry.py`**

Agregar `from bot.strategy.bollinger import decide_bollinger` y `"bollinger": decide_bollinger,` al dict `STRATEGIES`.

- [ ] **Step 6: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_indicators_bollinger.py tests/test_strategy_bollinger.py tests/test_strategy_registry.py -q` → PASS

- [ ] **Step 7: Commit**

```bash
git add bot/indicators.py bot/strategy/bollinger.py bot/strategy/registry.py tests/test_indicators_bollinger.py tests/test_strategy_bollinger.py
git commit -m "feat(strategy): Bollinger (reversion a la media)"
```

---

### Task 4: Estrategia Breakout (Donchian)

**Files:**
- Create: `bot/strategy/breakout.py`
- Modify: `bot/strategy/registry.py` (registrar `"breakout"`)
- Test: `tests/test_strategy_breakout.py`

**Interfaces:**
- Produces:
  - `decide_breakout(df, params: dict) -> Signal`: params `{lookback}` (default 20). `upper = max(high de las `lookback` velas previas)`, `lower = min(low de las previas)` (excluyendo la actual, vía `.shift(1)`). BUY cuando `close[-1] > upper[-1]`; SELL cuando `close[-1] < lower[-1]`; si no, HOLD. `indicators = {"donchian_upper", "donchian_lower"}`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_strategy_breakout.py
from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.breakout import decide_breakout


def _df(highs, lows, closes):
    n = len(closes)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": highs, "low": lows, "close": closes, "volume": [1] * n,
    })


def test_breakout_buys_above_prior_high():
    highs = [10] * 10 + [12]      # la última rompe el techo previo (10)
    lows = [8] * 11
    closes = [9] * 10 + [11]
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.BUY


def test_breakout_sells_below_prior_low():
    highs = [10] * 11
    lows = [8] * 10 + [6]
    closes = [9] * 10 + [5]       # cierra por debajo del piso previo (8)
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.SELL


def test_breakout_holds_inside_range():
    highs = [10] * 11
    lows = [8] * 11
    closes = [9] * 11
    sig = decide_breakout(_df(highs, lows, closes), {"lookback": 5})
    assert sig.action is Action.HOLD
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_breakout.py -q`
Expected: FAIL (`bot.strategy.breakout` no existe).

- [ ] **Step 3: Implementar la estrategia**

```python
# bot/strategy/breakout.py
from __future__ import annotations

import math

import pandas as pd

from bot.models import Action, Signal


def decide_breakout(df: pd.DataFrame, params: dict) -> Signal:
    lookback = params.get("lookback", 20)
    upper = df["high"].rolling(lookback).max().shift(1)
    lower = df["low"].rolling(lookback).min().shift(1)
    up = float(upper.iloc[-1])
    lo = float(lower.iloc[-1])
    close = float(df["close"].iloc[-1])
    ind = {"donchian_upper": up, "donchian_lower": lo}
    if math.isnan(up) or math.isnan(lo):
        return Signal(Action.HOLD, "Donchian sin datos suficientes", ind)
    if close > up:
        return Signal(Action.BUY, f"Ruptura del techo Donchian ({up:.2f})", ind)
    if close < lo:
        return Signal(Action.SELL, f"Ruptura del piso Donchian ({lo:.2f})", ind)
    return Signal(Action.HOLD, "Dentro del rango Donchian", ind)
```

- [ ] **Step 4: Registrar en `registry.py`**

Agregar `from bot.strategy.breakout import decide_breakout` y `"breakout": decide_breakout,` al dict `STRATEGIES`.

- [ ] **Step 5: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_breakout.py tests/test_strategy_registry.py -q` → PASS

- [ ] **Step 6: Commit**

```bash
git add bot/strategy/breakout.py bot/strategy/registry.py tests/test_strategy_breakout.py
git commit -m "feat(strategy): Breakout Donchian (ruptura de rango)"
```

---

### Task 5: Estrategia Price Action (patrones de vela)

**Files:**
- Create: `bot/strategy/price_action.py`
- Modify: `bot/strategy/registry.py` (registrar `"price_action"`)
- Test: `tests/test_strategy_price_action.py`

**Interfaces:**
- Produces:
  - `decide_price_action(df, params: dict) -> Signal`: params `{wick_ratio}` (default 2.0). Sobre la última vela `o,h,l,c` y la previa `po,ph,pl,pc`:
    - **Engulfing alcista** (`pc < po` y `c > o` y `o <= pc` y `c >= po`) → BUY.
    - **Engulfing bajista** (`pc > po` y `c < o` y `o >= pc` y `c <= po`) → SELL.
    - **Martillo** (cuerpo `|c-o|` > 0, mecha inferior `min(o,c)-l >= wick_ratio*|c-o|`, mecha superior `h-max(o,c) <= |c-o|`) → BUY.
    - **Estrella fugaz** (mecha superior `h-max(o,c) >= wick_ratio*|c-o|`, mecha inferior `min(o,c)-l <= |c-o|`) → SELL.
    - Orden de chequeo: engulfing antes que mecha; si nada, HOLD. `indicators = {"body", "upper_wick", "lower_wick"}`.

- [ ] **Step 1: Test que falla**

```python
# tests/test_strategy_price_action.py
from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.price_action import decide_price_action


def _df(rows):
    # rows: lista de (open, high, low, close)
    n = len(rows)
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": [r[0] for r in rows], "high": [r[1] for r in rows],
        "low": [r[2] for r in rows], "close": [r[3] for r in rows], "volume": [1] * n,
    })


def test_bullish_engulfing_buys():
    rows = [(10, 10.5, 9.5, 10), (10, 10.2, 8, 9), (9, 12, 8.9, 11.5)]
    # prev: bajista (open 10 -> close 9); curr: alcista que envuelve (open 9 <= 9, close 11.5 >= 10)
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.BUY


def test_bearish_engulfing_sells():
    rows = [(10, 10.5, 9.5, 10), (9, 11, 8.9, 10.5), (11, 11.2, 8.5, 9)]
    # prev: alcista (9 -> 10.5); curr: bajista que envuelve (open 11 >= 10.5, close 9 <= 9)
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.SELL


def test_hammer_buys():
    rows = [(10, 10.5, 9.5, 10), (10, 10.2, 9.8, 10.1)]
    # última: martillo (cuerpo 0.1, mecha inferior 10.0-... ). Construido para gatillar BUY.
    rows[-1] = (10.0, 10.1, 9.0, 10.05)  # cuerpo 0.05, mecha inf 1.0 (>= 2x cuerpo), mecha sup 0.05
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.BUY


def test_doji_inside_holds():
    rows = [(10, 10.5, 9.5, 10), (10, 10.6, 9.4, 10.1)]
    sig = decide_price_action(_df(rows), {"wick_ratio": 2.0})
    assert sig.action is Action.HOLD
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_price_action.py -q`
Expected: FAIL (`bot.strategy.price_action` no existe).

- [ ] **Step 3: Implementar la estrategia**

```python
# bot/strategy/price_action.py
from __future__ import annotations

import pandas as pd

from bot.models import Action, Signal


def decide_price_action(df: pd.DataFrame, params: dict) -> Signal:
    wick_ratio = params.get("wick_ratio", 2.0)
    o = float(df["open"].iloc[-1]); h = float(df["high"].iloc[-1])
    low = float(df["low"].iloc[-1]); c = float(df["close"].iloc[-1])
    po = float(df["open"].iloc[-2]); pc = float(df["close"].iloc[-2])

    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - low
    ind = {"body": body, "upper_wick": upper_wick, "lower_wick": lower_wick}

    # Engulfing (tiene prioridad sobre las mechas).
    if pc < po and c > o and o <= pc and c >= po:
        return Signal(Action.BUY, "Envolvente alcista", ind)
    if pc > po and c < o and o >= pc and c <= po:
        return Signal(Action.SELL, "Envolvente bajista", ind)

    # Mechas (martillo / estrella fugaz). Requiere cuerpo no nulo.
    if body > 0:
        if lower_wick >= wick_ratio * body and upper_wick <= body:
            return Signal(Action.BUY, "Martillo (mecha inferior larga)", ind)
        if upper_wick >= wick_ratio * body and lower_wick <= body:
            return Signal(Action.SELL, "Estrella fugaz (mecha superior larga)", ind)

    return Signal(Action.HOLD, "Sin patrón de price action", ind)
```

- [ ] **Step 4: Registrar en `registry.py`**

Agregar `from bot.strategy.price_action import decide_price_action` y `"price_action": decide_price_action,` al dict `STRATEGIES`.

- [ ] **Step 5: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_strategy_price_action.py tests/test_strategy_registry.py -q` → PASS

- [ ] **Step 6: Commit**

```bash
git add bot/strategy/price_action.py bot/strategy/registry.py tests/test_strategy_price_action.py
git commit -m "feat(strategy): Price Action (engulfing + martillo/estrella)"
```

---

### Task 6: Test de integración del registro completo

**Files:**
- Test: `tests/test_strategy_registry_full.py`

**Interfaces:**
- Consumes: `available()`, `get_strategy(name)` con las 5 estrategias registradas.

- [ ] **Step 1: Test que falla (todavía no están las 5 si se corre antes, pero acá ya sí)**

```python
# tests/test_strategy_registry_full.py
from __future__ import annotations

import pandas as pd

from bot.models import Signal
from bot.strategy.registry import available, get_strategy

EXPECTED = {"ema_rsi", "macd", "bollinger", "breakout", "price_action"}


def _flat_df(n=40):
    closes = [100.0] * n
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
    })


def test_all_five_registered():
    assert EXPECTED <= set(available())


def test_each_strategy_returns_signal_on_flat_market():
    df = _flat_df()
    for name in EXPECTED:
        sig = get_strategy(name)(df, {})
        assert isinstance(sig, Signal)
```

- [ ] **Step 2: Verificar verde + suite completa**

Run: `.venv/Scripts/python.exe -m pytest -q` → PASS (toda la suite)
Expected: todas las estrategias registradas; cada una devuelve un `Signal` válido en mercado plano (sin crashear por defaults faltantes).

- [ ] **Step 3: Commit**

```bash
git add tests/test_strategy_registry_full.py
git commit -m "test(strategy): integracion del registro con las 5 estrategias"
```

---

## Notas de cierre

- Tras la Fase 2, hay 5 estrategias puras y registradas, cada una probada con velas sintéticas. El motor **todavía no las usa** (sigue con `ema_rsi` para `default`).
- **Fase 3** cableará el registro al motor: cada cuenta levantará su estrategia con `get_strategy(account.strategy)(df, account.params)`, en un hilo por cuenta dentro de un solo contenedor.
- Los `indicators` de cada estrategia se devuelven en el `Signal` (para el motivo/visualización); por ahora el `Store` solo persiste columnas `ema_fast/ema_slow/rsi` (NaN para estrategias no-EMA). Persistencia genérica de indicadores = mejora futura (Fase 4 panel).
