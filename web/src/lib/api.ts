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
}
