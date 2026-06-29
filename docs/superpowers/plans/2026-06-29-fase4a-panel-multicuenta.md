# Fase 4a — Panel multi-cuenta (visibilidad) · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer visible y comparable la flota en el panel: un selector de cuenta que también rankea por P&L, toda la vista en vivo scopeada a la cuenta elegida, y un gráfico comparativo del P&L% de las 5 cuentas.

**Architecture:** El backend ya expone `GET /api/accounts` y acepta `?account=` en todos los endpoints; solo se le agrega `starting_cash` a `AccountOut` (para el P&L%). En el frontend, App mantiene el estado `account` (cuenta seleccionada), todos los fetches por cuenta usan `?account=`, un `AccountBar` lista las cuentas (selector + ranking) y un `ComparisonChart` superpone el P&L% de cada una.

**Tech Stack:** Python/FastAPI (backend), Vite + React 19 + TypeScript + Tailwind + recharts (frontend), pytest + vitest.

## Global Constraints

- Endpoints existentes ya account-aware (Fase 1/3): `/api/status|equity|positions|decisions|fills|candles?account=<id>` y `GET /api/accounts`. Default `account="default"`.
- P&L% de una cuenta = `(equity / starting_cash - 1) * 100`. Requiere `starting_cash` en `AccountOut` (Task 1).
- Tokens de diseño existentes: `gain-*` (verde, ganancia), `loss-*` (rojo, pérdida), `brand-*` (indigo), `zinc-*`, `font-display`, `font-mono`, `tabular-nums`. Helpers en `@/lib/format` (`formatUsd`, `actionLabel`, `formatCountdown`, `formatAgo`). Componentes UI shadcn en `@/components/ui` (card, badge, button, table, tabs).
- TDD donde aplique (backend pytest; api lib vitest). El frontend visual se valida con `npm run build` (tsc -b + vite) + `npm test` (vitest) verdes. `git add` específico (NUNCA `git add -A`).
- No romper los 137 tests de Python ni los 14 de vitest existentes.

---

### Task 1: `starting_cash` en `AccountOut`

**Files:**
- Modify: `api/models.py` (`AccountOut`)
- Modify: `api/app.py` (endpoint `accounts_list`)
- Test: `tests/test_api_accounts.py` (extender)

**Interfaces:**
- Produces: `AccountOut` con campo nuevo `starting_cash: float`. El endpoint `/api/accounts` lo completa desde la fila de la cuenta (`a["starting_cash"]`).

- [ ] **Step 1: Test que falla**

Agregar a `tests/test_api_accounts.py`:
```python
def test_accounts_include_starting_cash():
    from bot.store.db import Store
    store = Store(":memory:")
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2})
    store.record_equity("scalper", "2026-01-01T00:00:00+00:00", 10500.0, 9000.0)
    client = _client_with_store(store)
    body = client.get("/api/accounts").json()
    assert body[0]["starting_cash"] == 10000.0
    assert body[0]["equity"] == 10500.0
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_accounts.py::test_accounts_include_starting_cash -q`
Expected: FAIL (`KeyError`/validación: `starting_cash` no existe en `AccountOut`).

- [ ] **Step 3: Agregar el campo**

En `api/models.py`, dentro de `class AccountOut(BaseModel)`, agregar tras `enabled: bool`:
```python
    starting_cash: float
```
En `api/app.py`, en el armado de `AccountOut(...)` dentro de `accounts_list`, agregar el kwarg:
```python
                starting_cash=a["starting_cash"],
```

- [ ] **Step 4: Verificar verde**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api_accounts.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add api/models.py api/app.py tests/test_api_accounts.py
git commit -m "feat(api): starting_cash en AccountOut (para P&L del panel)"
```

---

### Task 2: Tipos + cliente API por cuenta

**Files:**
- Modify: `web/src/lib/types.ts` (interface `Account`)
- Modify: `web/src/lib/api.ts` (`getAccounts`, `getAllAccountsEquity`, param `account` en los getters)
- Modify: `web/src/lib/use-polling.ts` (deps opcionales)
- Test: `web/src/lib/api.test.ts` (nuevo)

**Interfaces:**
- Produces:
  - `Account { id, name, strategy, symbol, timeframe, interval_seconds, ai_enabled, enabled, equity, cash, starting_cash }`.
  - `api.getAccounts() -> Promise<Account[]>`.
  - getters con `account?: string`: `getStatus(account?)`, `getEquity(limit?, account?)`, `getPositions(account?)`, `getDecisions(limit?, account?)`, `getFills(limit?, account?)`, `getCandles(symbol?, timeframe?, limit?, account?)`. Cada uno agrega `?account=<id>` si viene.
  - `api.getAllAccountsEquity(ids: string[], limit?) -> Promise<Record<string, EquityPoint[]>>` (Promise.all de `getEquity` por id).
  - `usePolling(fn, intervalMs, deps?: unknown[])`: re-ejecuta el efecto (refetch inmediato) cuando cambian `deps`.

- [ ] **Step 1: Test que falla**

```typescript
// web/src/lib/api.test.ts
import { afterEach, expect, test, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.restoreAllMocks())

function mockFetch(captured: string[]) {
  vi.stubGlobal('fetch', (url: string) => {
    captured.push(url)
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  })
}

test('getStatus adds account query', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getStatus('scalper')
  expect(urls[0]).toContain('/api/status?account=scalper')
})

test('getCandles keeps limit and adds account', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getCandles(undefined, undefined, 50, 'momentum')
  expect(urls[0]).toContain('limit=50')
  expect(urls[0]).toContain('account=momentum')
})

test('getAccounts hits /api/accounts', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getAccounts()
  expect(urls[0]).toContain('/api/accounts')
})
```

- [ ] **Step 2: Verificar que falla**

Run (en `web/`): `npm test -- api.test.ts`
Expected: FAIL (`getStatus` no acepta arg; `getAccounts` no existe).

- [ ] **Step 3: Agregar `Account` a `types.ts`**

Agregar al final de `web/src/lib/types.ts`:
```typescript
export interface Account {
  id: string
  name: string
  strategy: string
  symbol: string
  timeframe: string
  interval_seconds: number
  ai_enabled: boolean
  enabled: boolean
  equity: number
  cash: number
  starting_cash: number
}
```

- [ ] **Step 4: Reescribir `api.ts`**

```typescript
import type { Account, Candle, Decision, EquityPoint, Fill, Position, Status } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status} en ${path}`)
  return (await res.json()) as T
}

function q(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const api = {
  getAccounts: () => getJson<Account[]>('/api/accounts'),
  getStatus: (account?: string) => getJson<Status>(`/api/status${q({ account })}`),
  getEquity: (limit = 200, account?: string) =>
    getJson<EquityPoint[]>(`/api/equity${q({ limit, account })}`),
  getPositions: (account?: string) => getJson<Position[]>(`/api/positions${q({ account })}`),
  getDecisions: (limit = 20, account?: string) =>
    getJson<Decision[]>(`/api/decisions${q({ limit, account })}`),
  getFills: (limit = 50, account?: string) =>
    getJson<Fill[]>(`/api/fills${q({ limit, account })}`),
  getCandles: (symbol?: string, timeframe?: string, limit = 120, account?: string) =>
    getJson<Candle[]>(`/api/candles${q({ symbol, timeframe, limit, account })}`),
  getAllAccountsEquity: async (ids: string[], limit = 200): Promise<Record<string, EquityPoint[]>> => {
    const series = await Promise.all(
      ids.map((id) => getJson<EquityPoint[]>(`/api/equity${q({ limit, account: id })}`)),
    )
    const out: Record<string, EquityPoint[]> = {}
    ids.forEach((id, i) => { out[id] = series[i] })
    return out
  },
}
```

- [ ] **Step 5: Deps en `use-polling.ts`**

En `web/src/lib/use-polling.ts`, cambiar la firma y las deps del efecto:
```typescript
export function usePolling<T>(
  fn: () => Promise<T>,
  intervalMs: number,
  deps: unknown[] = [],
): PollingState<T> {
```
y la línea del efecto `}, [intervalMs])` por:
```typescript
  }, [intervalMs, ...deps])
```
(El resto del hook queda igual; `fnRef.current = fn` ya está.)

- [ ] **Step 6: Verificar verde**

Run (en `web/`): `npm test -- api.test.ts` → PASS. Y `npm test` (toda la suite vitest) → PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/lib/types.ts web/src/lib/api.ts web/src/lib/use-polling.ts web/src/lib/api.test.ts
git commit -m "feat(web): cliente API por cuenta + getAccounts + usePolling con deps"
```

---

### Task 3: `AccountBar` (selector + ranking) y estado de cuenta en App

**Files:**
- Create: `web/src/components/AccountBar.tsx`
- Modify: `web/src/App.tsx` (estado `account`, fetch de cuentas, fetches por cuenta, render del `AccountBar`)
- Test: build + vitest

**Interfaces:**
- Consumes: `api.getAccounts`, `Account`, `usePolling`, `formatUsd`.
- Produces:
  - `AccountBar({ accounts, selected, onSelect }: { accounts: Account[]; selected: string | null; onSelect: (id: string) => void })`: fila de pills, una por cuenta, ordenadas por P&L% desc. Cada pill: nombre, badge de estrategia, P&L% coloreado (`gain`/`loss`), punto "vivo"; la seleccionada resaltada (ring `brand`). Click → `onSelect(id)`.

- [ ] **Step 1: Crear `AccountBar.tsx`**

```tsx
import type { Account } from '@/lib/types'
import { formatUsd } from '@/lib/format'

function pnlPct(a: Account): number {
  if (!a.starting_cash) return 0
  return (a.equity / a.starting_cash - 1) * 100
}

export function AccountBar({
  accounts,
  selected,
  onSelect,
}: {
  accounts: Account[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  const ranked = [...accounts].sort((a, b) => pnlPct(b) - pnlPct(a))
  return (
    <div className="flex flex-wrap gap-2">
      {ranked.map((a, i) => {
        const pnl = pnlPct(a)
        const isSel = a.id === selected
        const tone = pnl > 0 ? 'text-gain-700' : pnl < 0 ? 'text-loss-700' : 'text-zinc-500'
        return (
          <button
            key={a.id}
            onClick={() => onSelect(a.id)}
            className={
              'flex min-w-[8.5rem] flex-col items-start rounded-xl border px-3 py-2 text-left transition ' +
              (isSel
                ? 'border-brand-300 bg-brand-50 ring-2 ring-inset ring-brand-200'
                : 'border-zinc-200 bg-white hover:border-zinc-300')
            }
          >
            <div className="flex w-full items-center justify-between gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                #{i + 1}
              </span>
              {a.enabled ? (
                <span className="h-1.5 w-1.5 rounded-full bg-gain-500" aria-label="activa" />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-300" aria-label="pausada" />
              )}
            </div>
            <span className="font-display text-sm font-semibold text-zinc-900">{a.name}</span>
            <span className="text-[11px] text-zinc-500">{a.strategy}</span>
            <span className={`mt-1 font-mono text-sm font-semibold tabular-nums ${tone}`}>
              {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}%
            </span>
            <span className="font-mono text-[11px] text-zinc-400 tabular-nums">
              {formatUsd(a.equity)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Cablear estado de cuenta en `App.tsx`**

Reemplazar `web/src/App.tsx` por la versión con estado `account` (cambios marcados; mantené el resto del layout igual):
```tsx
import { useCallback, useEffect, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { AccountBar } from '@/components/AccountBar'
import { ActivityLog } from '@/components/ActivityLog'
import { EquityChart } from '@/components/EquityChart'
import { HistoryTable } from '@/components/HistoryTable'
import { KpiRow } from '@/components/KpiRow'
import { LiveAnalysis } from '@/components/LiveAnalysis'
import { LivePriceChart } from '@/components/LivePriceChart'
import { NextRunCard } from '@/components/NextRunCard'
import { PositionsTable } from '@/components/PositionsTable'
import { TopBar } from '@/components/TopBar'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const LIVE_INTERVAL = 2500
const SLOW_INTERVAL = 5000

export default function App() {
  const accounts = usePolling(useCallback(() => api.getAccounts(), []), SLOW_INTERVAL)
  const accountList = accounts.data ?? []
  const [account, setAccount] = useState<string | null>(null)

  // Selección inicial: primera cuenta cuando llega la lista.
  useEffect(() => {
    if (account === null && accountList.length > 0) setAccount(accountList[0].id)
  }, [account, accountList])

  const acc = account ?? undefined

  const status = usePolling(useCallback(() => api.getStatus(acc), [acc]), LIVE_INTERVAL, [account])
  const candles = usePolling(useCallback(() => api.getCandles(undefined, undefined, 120, acc), [acc]), LIVE_INTERVAL, [account])
  const decisions = usePolling(useCallback(() => api.getDecisions(20, acc), [acc]), LIVE_INTERVAL, [account])
  const positions = usePolling(useCallback(() => api.getPositions(acc), [acc]), LIVE_INTERVAL, [account])
  const equity = usePolling(useCallback(() => api.getEquity(200, acc), [acc]), SLOW_INTERVAL, [account])
  const fills = usePolling(useCallback(() => api.getFills(50, acc), [acc]), SLOW_INTERVAL, [account])

  const series = equity.data ?? []
  const decisionList = decisions.data ?? []
  const candleList = candles.data ?? []
  const positionList = positions.data ?? []
  const fillList = fills.data ?? []

  const symbol = status.data?.symbols?.[0] ?? ''
  const timeframe = status.data?.timeframe ?? ''
  const strategy = status.data?.strategy ?? null
  const openPosition = positionList.find((p) => p.symbol === symbol) ?? positionList[0] ?? null
  const lastClose = candleList.length ? candleList[candleList.length - 1].close : null

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <div className="accent-top h-1 w-full" />
      <TopBar status={status.data} />
      <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
        {status.error && (
          <div className="flex items-start gap-2.5 rounded-lg bg-loss-50 px-4 py-3 text-sm text-loss-700 ring-1 ring-inset ring-loss-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>No se pudo conectar con la API.</span>
          </div>
        )}

        {accountList.length > 0 && (
          <AccountBar accounts={accountList} selected={account} onSelect={setAccount} />
        )}

        <KpiRow status={status.data} series={series} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LivePriceChart
              candles={candleList}
              fills={fillList}
              position={openPosition}
              strategy={strategy}
              symbol={symbol}
              timeframe={timeframe}
            />
          </div>
          <NextRunCard status={status.data} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <LiveAnalysis decision={decisionList[0] ?? null} lastClose={lastClose} strategy={strategy} />
          <div className="lg:col-span-2">
            <EquityChart series={series} />
          </div>
        </div>

        <PositionsTable positions={positionList} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HistoryTable fills={fillList} />
          <ActivityLog decisions={decisionList} />
        </div>
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Verificar build + vitest**

Run (en `web/`): `npm run build` → OK (sin errores de tipos). `npm test` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/AccountBar.tsx web/src/App.tsx
git commit -m "feat(web): selector de cuenta + ranking (AccountBar) y vista scopeada por cuenta"
```

---

### Task 4: `ComparisonChart` (P&L% de las 5 superpuesto)

**Files:**
- Create: `web/src/components/ComparisonChart.tsx`
- Modify: `web/src/App.tsx` (render del `ComparisonChart`)
- Test: build + vitest

**Interfaces:**
- Consumes: `api.getAllAccountsEquity`, `Account`, `EquityPoint`, recharts.
- Produces: `ComparisonChart({ accounts }: { accounts: Account[] })`: por cada cuenta toma su serie de equity, la convierte a P&L% (`equity/starting_cash - 1`) y las superpone alineadas por índice de paso (no por reloj). Una `Line` por cuenta. Maneja series de distinto largo con `connectNulls`.

- [ ] **Step 1: Crear `ComparisonChart.tsx`**

```tsx
import { useCallback } from 'react'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { Account } from '@/lib/types'
import { usePolling } from '@/lib/use-polling'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7']

export function ComparisonChart({ accounts }: { accounts: Account[] }) {
  const ids = accounts.map((a) => a.id)
  const idsKey = ids.join(',')
  const series = usePolling(
    useCallback(() => api.getAllAccountsEquity(ids, 200), [idsKey]),
    5000,
    [idsKey],
  )
  const byId = series.data ?? {}
  const start: Record<string, number> = {}
  accounts.forEach((a) => { start[a.id] = a.starting_cash || 10000 })

  // Alinear por índice de paso: fila i = P&L% de cada cuenta en su i-ésimo punto.
  const maxLen = Math.max(0, ...accounts.map((a) => (byId[a.id]?.length ?? 0)))
  const data = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | null> = { i }
    for (const a of accounts) {
      const pts = byId[a.id]
      row[a.id] = pts && pts[i] ? (pts[i].equity / start[a.id] - 1) * 100 : null
    }
    return row
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">
          Comparativa de estrategias · P&amp;L %
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72 w-full">
          {maxLen === 0 ? (
            <p className="pt-8 text-center text-sm text-zinc-400">
              Esperando datos de las cuentas…
            </p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f4" />
                <XAxis dataKey="i" tick={{ fontSize: 11, fill: '#a1a1aa' }} />
                <YAxis tick={{ fontSize: 11, fill: '#a1a1aa' }} width={48}
                       tickFormatter={(v) => `${Number(v).toFixed(1)}%`} />
                <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} />
                <Legend />
                {accounts.map((a, idx) => (
                  <Line key={a.id} type="monotone" dataKey={a.id} name={a.name}
                        stroke={COLORS[idx % COLORS.length]} strokeWidth={2}
                        dot={false} connectNulls isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Render en `App.tsx`**

En `web/src/App.tsx`, importar el componente:
```tsx
import { ComparisonChart } from '@/components/ComparisonChart'
```
y agregarlo después del `AccountBar` (antes de `KpiRow`):
```tsx
        {accountList.length > 1 && <ComparisonChart accounts={accountList} />}
```

- [ ] **Step 3: Verificar build + vitest**

Run (en `web/`): `npm run build` → OK. `npm test` → PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ComparisonChart.tsx web/src/App.tsx
git commit -m "feat(web): grafico comparativo de P&L% de las 5 cuentas"
```

---

### Task 5: Verificación final del panel

**Files:**
- Test: build + vitest completos

- [ ] **Step 1: Build y tests verdes**

Run (en `web/`):
```
npm run build
npm test
```
Expected: build sin errores de tipos; toda la suite vitest verde (los 14 previos + los nuevos de api.test).

- [ ] **Step 2: (Opcional) limpiar `dep`/`void dep`**

Si quedó el `const dep`/`void dep` de la Task 3 y preferís sin él, borralo y re-verificá el build.

- [ ] **Step 3: Commit (si hubo cambios)**

```bash
git add web/
git commit -m "chore(web): verificacion final panel multi-cuenta"
```

---

## Notas de cierre

- Tras la Fase 4a, el panel muestra el **AccountBar** (selector + ranking por P&L), toda la vista en vivo **scopeada a la cuenta elegida**, y el **ComparisonChart** con el P&L% de las 5 superpuesto. La flota deja de ser invisible.
- El controlador (no un subagente) reconstruye la imagen Docker y hace el smoke-test del panel multi-cuenta tras esta fase.
- **Fase 4b** (siguiente): edición de config por cuenta desde el panel (`PUT /api/accounts/{id}` + hot-reload de la flota + formulario), y enable/disable de cuentas.
