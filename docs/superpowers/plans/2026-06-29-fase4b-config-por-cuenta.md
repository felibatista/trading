# Fase 4b — Config por cuenta desde el panel (hot-reload) · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Editar la config de cada cuenta desde el panel (estrategia, params, timeframe, intervalo, IA on/off, pausar/reanudar) y que la flota la tome **en caliente**, sin reiniciar el contenedor.

**Architecture:** Nuevo `PUT /api/accounts/{id}` valida y mergea los cambios en la tabla `accounts`. La flota corre un hilo por cuenta que, en cada iteración, **relee la cuenta** y reconstruye su `Engine` si la config cambió (o queda en idle si la cuenta está pausada). El frontend agrega un modal de config por cuenta que hace el PUT.

**Tech Stack:** FastAPI/Pydantic, threading, React + TS + Tailwind, pytest + vitest.

## Global Constraints

- `PUT /api/accounts/{id}`: cuerpo parcial (todos los campos opcionales); se mergea sobre la cuenta actual y se reescribe con `store.upsert_account`. 404 si la cuenta no existe; 422/400 si la validación falla.
- Validación: `strategy` ∈ {ema_rsi, macd, bollinger, breakout, price_action}; `timeframe` ∈ {1m,3m,5m,15m,30m,1h,2h,4h,1d}; `interval_seconds` 5..86400; `params` es objeto; `ai_enabled`/`enabled` bool.
- La flota toma cambios en ≤ el intervalo de la cuenta. Una cuenta pausada (`enabled=false`) no opera pero su hilo sigue vivo (se reanuda al re-habilitar).
- Reconstruir el engine re-hidrata el broker desde el store (cash/holdings), así no se pierde el estado de la cuenta.
- No romper los 138 pytest ni los 17 vitest existentes. TDD. `git add` específico (NUNCA `git add -A`).

---

### Task 1: `PUT /api/accounts/{id}`

**Files:**
- Modify: `api/models.py` (`AccountUpdate`)
- Modify: `api/app.py` (endpoint `update_account`)
- Test: `tests/test_api_account_update.py`

**Interfaces:**
- Produces:
  - `AccountUpdate(BaseModel)` con todos los campos opcionales: `name, strategy, symbol, timeframe, interval_seconds, starting_cash, ai_enabled, enabled, params`, con validadores de rango/enum.
  - `PUT /api/accounts/{account_id}` → mergea sobre `store.get_account(id)`; si no existe → 404; reescribe con `store.upsert_account`; devuelve `AccountOut` actualizado.

- [ ] **Step 1: Test que falla**

```python
# tests/test_api_account_update.py
from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_store
from bot.store.db import Store


def _client(store):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def _seed(store):
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2, "slow": 4})


def test_put_updates_editable_fields():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    r = client.put("/api/accounts/scalper", json={
        "timeframe": "5m", "interval_seconds": 30, "ai_enabled": False,
        "enabled": False, "params": {"fast": 3, "slow": 9},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["timeframe"] == "5m" and body["ai_enabled"] is False and body["enabled"] is False
    acc = store.get_account("scalper")
    assert acc["params"] == {"fast": 3, "slow": 9} and acc["interval_seconds"] == 30


def test_put_unknown_account_404():
    store = Store(":memory:")
    client = _client(store)
    assert client.put("/api/accounts/noexiste", json={"enabled": False}).status_code == 404


def test_put_rejects_bad_strategy():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    assert client.put("/api/accounts/scalper", json={"strategy": "inventada"}).status_code == 422


def test_put_rejects_bad_interval():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    assert client.put("/api/accounts/scalper", json={"interval_seconds": 1}).status_code == 422
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_account_update.py -q`
Expected: FAIL (no existe el endpoint PUT).

- [ ] **Step 3: `AccountUpdate` en `api/models.py`**

Agregar (importar `Field`, `field_validator` de pydantic arriba si falta):
```python
from pydantic import BaseModel, Field, field_validator

_STRATS = {"ema_rsi", "macd", "bollinger", "breakout", "price_action"}
_TFS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"}


class AccountUpdate(BaseModel):
    name: str | None = None
    strategy: str | None = None
    symbol: str | None = None
    timeframe: str | None = None
    interval_seconds: int | None = Field(default=None, ge=5, le=86400)
    starting_cash: float | None = Field(default=None, gt=0)
    ai_enabled: bool | None = None
    enabled: bool | None = None
    params: dict | None = None

    @field_validator("strategy")
    @classmethod
    def _v_strategy(cls, v: str | None) -> str | None:
        if v is not None and v not in _STRATS:
            raise ValueError(f"strategy inválida: {v}")
        return v

    @field_validator("timeframe")
    @classmethod
    def _v_timeframe(cls, v: str | None) -> str | None:
        if v is not None and v not in _TFS:
            raise ValueError(f"timeframe inválido: {v}")
        return v
```

- [ ] **Step 4: Endpoint en `api/app.py`**

Importar `AccountUpdate` y `HTTPException`:
```python
from fastapi import Depends, FastAPI, HTTPException
from api.models import (AccountOut, AccountUpdate, CandleOut, DecisionOut,
                        EquityPoint, FillOut, PositionOut, StatusResponse, StrategyOut)
```
Agregar el endpoint (después de `accounts_list`):
```python
    @app.put("/api/accounts/{account_id}", response_model=AccountOut)
    def update_account(
        account_id: str, patch: AccountUpdate, store: Store = Depends(get_store),
    ) -> AccountOut:
        current = store.get_account(account_id)
        if current is None:
            raise HTTPException(status_code=404, detail="cuenta no encontrada")
        data = {**current, **patch.model_dump(exclude_none=True)}
        store.upsert_account(
            account_id, data["name"], data["strategy"], data["symbol"],
            data["timeframe"], data["interval_seconds"], data["starting_cash"],
            data["ai_enabled"], data["enabled"], data["params"],
        )
        eq = store.latest_equity(account_id)
        equity_v, cash = eq if eq is not None else (data["starting_cash"], data["starting_cash"])
        return AccountOut(
            id=account_id, name=data["name"], strategy=data["strategy"],
            symbol=data["symbol"], timeframe=data["timeframe"],
            interval_seconds=data["interval_seconds"], ai_enabled=data["ai_enabled"],
            enabled=data["enabled"], equity=equity_v, cash=cash,
            starting_cash=data["starting_cash"],
        )
```

- [ ] **Step 5: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_account_update.py -q` → PASS

- [ ] **Step 6: Commit**

```bash
git add api/models.py api/app.py tests/test_api_account_update.py
git commit -m "feat(api): PUT /api/accounts/{id} con validacion (config editable)"
```

---

### Task 2: Hot-reload de la flota

**Files:**
- Modify: `bot/fleet.py` (hilo por cuenta que relee y reconstruye; idle si pausada)
- Test: `tests/test_fleet_hotreload.py`

**Interfaces:**
- Produces:
  - `Fleet._config_sig(account: dict) -> tuple`: firma de la config relevante `(strategy, json params ordenado, symbol, timeframe, ai_enabled)`.
  - `Fleet.start()`: lanza un hilo por **cada** cuenta (habilitada o no), por id.
  - `Fleet._loop(account_id)`: cada iteración relee `store.get_account(id)`; si no existe → termina; si `enabled` es False → espera y sigue (idle); si la firma cambió (o es la 1ª vez) → reconstruye el engine; corre `run_cycle(symbol)`; espera `interval_seconds` actual.
  - `Fleet.run_once()`: corre un ciclo por cada cuenta habilitada releyendo el estado actual (reconstruye el engine en cada llamada).

- [ ] **Step 1: Test que falla**

```python
# tests/test_fleet_hotreload.py
from __future__ import annotations

import pandas as pd

from bot.config import Config
from bot.fleet import Fleet
from bot.store.db import Store


def _feed():
    class F:
        def fetch_ohlcv(self, symbol, timeframe, limit=200):
            closes = [100.0 + (i % 5) for i in range(40)]
            n = len(closes)
            return pd.DataFrame({
                "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
                "open": closes, "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes], "close": closes, "volume": [1] * n,
            })
    return F()


def _seed(store, enabled=True):
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 1,
                         10000.0, False, enabled, {"fast": 2, "slow": 4})


def test_config_sig_changes_with_params():
    store = Store(":memory:")
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    a1 = {"strategy": "ema_rsi", "params": {"fast": 2}, "symbol": "BTC/USDT",
          "timeframe": "1m", "ai_enabled": False}
    a2 = {**a1, "params": {"fast": 3}}
    assert fleet._config_sig(a1) != fleet._config_sig(a2)
    store.close()


def test_run_once_respects_live_enabled_flag():
    store = Store(":memory:")
    _seed(store, enabled=True)
    fleet = Fleet(store, Config(), feed_factory=lambda: _feed())
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 1
    # pausar -> no opera
    store.set_account_enabled("scalper", False)
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 1
    # reanudar -> vuelve a operar
    store.set_account_enabled("scalper", True)
    fleet.run_once()
    assert len(store.recent_decisions("scalper")) == 2
    store.close()
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_fleet_hotreload.py -q`
Expected: FAIL (`_config_sig` no existe; `run_once` cachea con `_setup` y no relee el flag).

- [ ] **Step 3: Reescribir el cuerpo dinámico de `Fleet`**

En `bot/fleet.py`:
1. Agregar `import json` arriba.
2. Reemplazar `_setup`, `run_once`, `_loop`, `start` por:
```python
    @staticmethod
    def _config_sig(account: dict) -> tuple:
        return (
            account["strategy"],
            json.dumps(account.get("params") or {}, sort_keys=True),
            account["symbol"],
            account["timeframe"],
            bool(account["ai_enabled"]),
        )

    def run_once(self) -> None:
        for account in self.store.list_accounts():
            if not account["enabled"]:
                continue
            try:
                engine = self._build_engine(account)
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001 - aislar fallos por cuenta
                self.log(f"[{account['id']}] ERROR: {exc}")

    def _loop(self, account_id: str) -> None:
        engine = None
        sig = None
        while not self._stop.is_set():
            account = self.store.get_account(account_id)
            if account is None:
                return
            interval = account["interval_seconds"]
            if not account["enabled"]:
                self._stop.wait(interval)
                continue
            new_sig = self._config_sig(account)
            if engine is None or new_sig != sig:
                try:
                    engine = self._build_engine(account)
                    sig = new_sig
                    self.log(f"[{account_id}] config (re)cargada")
                except Exception as exc:  # noqa: BLE001
                    self.log(f"[{account_id}] ERROR al construir engine: {exc}")
                    self._stop.wait(interval)
                    continue
            try:
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001
                self.log(f"[{account_id}] ERROR: {exc}")
            self._stop.wait(interval)

    def start(self) -> None:
        self._stop.clear()
        for account in self.store.list_accounts():
            t = threading.Thread(
                target=self._loop, args=(account["id"],),
                name=f"fleet-{account['id']}", daemon=True,
            )
            t.start()
            self._threads.append(t)
        self.log(f"Flota arriba: {len(self._threads)} cuentas")
```
3. Borrar el atributo `self._pairs` del `__init__` (ya no se usa). Dejar `self._threads` y `self._stop`.

(`_build_broker` y `_build_engine` quedan igual que en la Fase 3.)

- [ ] **Step 4: Verificar verde (nuevo + fleet previo)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_fleet_hotreload.py tests/test_fleet.py tests/test_fleet_integration.py -q` → PASS
(Si `test_fleet.py::test_start_then_stop_is_clean` usaba `fleet._pairs`, sigue válido: `start()` ahora llena `_threads`; el assert sobre `_threads` no cambia.)

- [ ] **Step 5: Commit**

```bash
git add bot/fleet.py tests/test_fleet_hotreload.py
git commit -m "feat(fleet): hot-reload por cuenta (relee config, reconstruye, idle si pausada)"
```

---

### Task 3: Modal de config por cuenta en el panel

**Files:**
- Modify: `web/src/lib/api.ts` (`updateAccount`)
- Create: `web/src/components/AccountConfig.tsx`
- Modify: `web/src/App.tsx` (botón de config en la cuenta seleccionada + modal; fix del flash de `default`)
- Test: build + vitest

**Interfaces:**
- Produces:
  - `api.updateAccount(id: string, patch: Partial<...>) -> Promise<Account>` (PUT JSON).
  - `AccountConfig({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void })`: modal con campos enabled (toggle), ai_enabled (toggle), strategy (select de las 5), timeframe (select), interval_seconds (number), params (textarea JSON). "Guardar" valida el JSON, hace el PUT y, en éxito, llama `onSaved` + `onClose`; muestra el error del backend si falla.
  - En `App.tsx`: estado `configOpen` (bool); botón "Config" que lo abre para la cuenta seleccionada; los fetches en vivo NO piden cuando `account === null` (fix del flash).

- [ ] **Step 1: `updateAccount` en `api.ts`**

Agregar dentro del objeto `api` (después de `getAllAccountsEquity`):
```typescript
  updateAccount: async (id: string, patch: Record<string, unknown>): Promise<Account> => {
    const res = await fetch(`${BASE}/api/accounts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try { const j = await res.json(); detail = JSON.stringify(j.detail ?? j) } catch { /* noop */ }
      throw new Error(detail)
    }
    return (await res.json()) as Account
  },
```

- [ ] **Step 2: Crear `AccountConfig.tsx`**

```tsx
import { useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { Account } from '@/lib/types'

const STRATS = ['ema_rsi', 'macd', 'bollinger', 'breakout', 'price_action']
const TFS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']

export function AccountConfig({
  account, onClose, onSaved,
}: {
  account: Account
  onClose: () => void
  onSaved: () => void
}) {
  const [enabled, setEnabled] = useState(account.enabled)
  const [aiEnabled, setAiEnabled] = useState(account.ai_enabled)
  const [strategy, setStrategy] = useState(account.strategy)
  const [timeframe, setTimeframe] = useState(account.timeframe)
  const [interval, setIntervalS] = useState(account.interval_seconds)
  const [paramsText, setParamsText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // params actuales no vienen en Account; se editan como JSON (vacío = no cambiar).
  async function save() {
    setError(null)
    const patch: Record<string, unknown> = {
      enabled, ai_enabled: aiEnabled, strategy, timeframe, interval_seconds: Number(interval),
    }
    if (paramsText.trim()) {
      try { patch.params = JSON.parse(paramsText) } catch { setError('params: JSON inválido'); return }
    }
    setSaving(true)
    try {
      await api.updateAccount(account.id, patch)
      onSaved()
      onClose()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-zinc-900">Config · {account.name}</h2>
          <button onClick={onClose} aria-label="Cerrar" className="text-zinc-400 hover:text-zinc-700">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 text-sm">
          <label className="flex items-center justify-between">
            <span className="text-zinc-600">Activa</span>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-zinc-600">IA (veto de entradas)</span>
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} />
          </label>
          <label className="block">
            <span className="text-zinc-600">Estrategia</span>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
                    className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5">
              {STRATS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-600">Timeframe</span>
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}
                    className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5">
              {TFS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-600">Intervalo (segundos)</span>
            <input type="number" min={5} value={interval}
                   onChange={(e) => setIntervalS(Number(e.target.value))}
                   className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5 tabular-nums" />
          </label>
          <label className="block">
            <span className="text-zinc-600">Params (JSON, vacío = no cambiar)</span>
            <textarea value={paramsText} onChange={(e) => setParamsText(e.target.value)}
                      placeholder='{"fast": 2, "slow": 4}' rows={3}
                      className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5 font-mono text-xs" />
          </label>
          {error && <p className="rounded-md bg-loss-50 px-3 py-2 text-loss-700">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" onClick={save} disabled={saving}>{saving ? 'Guardando…' : 'Guardar'}</Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Cablear en `App.tsx`**

1. Importar:
```tsx
import { Settings } from 'lucide-react'
import { AccountConfig } from '@/components/AccountConfig'
```
2. Estado del modal (junto a los demás useState):
```tsx
  const [configOpen, setConfigOpen] = useState(false)
  const selectedAccount = accountList.find((a) => a.id === account) ?? null
```
3. **Fix del flash**: que los 6 fetches en vivo no pidan mientras `account` es null. Cambiar cada `useCallback` así (mismo patrón para los 6):
```tsx
  const status = usePolling(useCallback(() => acc ? api.getStatus(acc) : Promise.resolve(null), [acc]), LIVE_INTERVAL, [account])
  const candles = usePolling(useCallback(() => acc ? api.getCandles(undefined, undefined, 120, acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const decisions = usePolling(useCallback(() => acc ? api.getDecisions(20, acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const positions = usePolling(useCallback(() => acc ? api.getPositions(acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const equity = usePolling(useCallback(() => acc ? api.getEquity(200, acc) : Promise.resolve([]), [acc]), SLOW_INTERVAL, [account])
  const fills = usePolling(useCallback(() => acc ? api.getFills(50, acc) : Promise.resolve([]), [acc]), SLOW_INTERVAL, [account])
```
4. Botón de config + render del modal. Junto al `AccountBar`:
```tsx
        {accountList.length > 0 && (
          <div className="flex items-center justify-between gap-3">
            <AccountBar accounts={accountList} selected={account} onSelect={setAccount} />
            {selectedAccount && (
              <Button variant="outline" size="sm" onClick={() => setConfigOpen(true)}>
                <Settings className="h-4 w-4" /> Config
              </Button>
            )}
          </div>
        )}
        {configOpen && selectedAccount && (
          <AccountConfig
            account={selectedAccount}
            onClose={() => setConfigOpen(false)}
            onSaved={() => {}}
          />
        )}
```
Nota: `onSaved` queda como no-op a propósito — `usePolling` no expone `refetch` y el polling de cuentas (cada 5s) refleja el cambio solo. Importá `Button` desde `@/components/ui/button` si no está importado en `App.tsx`.

- [ ] **Step 4: Verificar build + vitest**

Run (en `web/`): `npm run build` → OK (0 errores de tipo). `npm test` → PASS (17).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/components/AccountConfig.tsx web/src/App.tsx
git commit -m "feat(web): modal de config por cuenta (PUT) + fix flash de cuenta default"
```

---

### Task 4: Verificación final

**Files:** ninguno (verificación)

- [ ] **Step 1: Suites completas**

Run: `.venv/Scripts/python.exe -m pytest -q` → PASS (todos los backend).
Run (en `web/`): `npm run build` && `npm test` → ambos verdes.

- [ ] **Step 2: (Si quedó algo sin commitear) commit**

```bash
git status --short
```
Si hay cambios pendientes de los pasos anteriores, commitealos con `git add` específico.

---

## Notas de cierre

- Tras la Fase 4b, desde el panel se edita cada cuenta (estrategia/params/timeframe/intervalo/IA/pausa) y la flota lo toma **en caliente** (≤ el intervalo de la cuenta), sin reiniciar el contenedor. Prender la IA de una cuenta es un toggle (necesita `ANTHROPIC_API_KEY` en el entorno; si no está, esa cuenta cae a solo-reglas).
- El controlador reconstruye la imagen y hace el smoke-test: PUT a una cuenta y verificar en los logs el `[id] config (re)cargada` y el cambio de comportamiento.
- Con esto el árbol multi-cuenta está completo (Fases 1–4). Mejora futura opcional: riesgo por cuenta (hoy global) y alta/baja de cuentas nuevas desde el panel.
