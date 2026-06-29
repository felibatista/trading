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
