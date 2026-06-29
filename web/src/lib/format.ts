import type { EquityPoint } from './types'

export function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/**
 * `value.toFixed(digits)` tolerante a nulos: devuelve "—" si el valor es
 * null/undefined/NaN. Indicadores específicos de estrategia (ema_fast, rsi…)
 * llegan null desde la API cuando la estrategia no los produce (p. ej. MACD),
 * porque el backend guarda NaN y pydantic lo serializa como null.
 */
export function fixed(value: number | null | undefined, digits: number): string {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

export function formatPct(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(2)}%`
}

export function pnlColor(value: number): string {
  if (value > 0) return 'text-gain-700'
  if (value < 0) return 'text-loss-600'
  return 'text-zinc-500'
}

// Direction of a value, decoupled from color so the UI never relies on color alone
// (Refactoring UI: pair color with an icon/shape). -1 down, 0 flat, 1 up.
export type Trend = -1 | 0 | 1

export function trend(value: number): Trend {
  if (value > 0) return 1
  if (value < 0) return -1
  return 0
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

/** Segundos -> "mm:ss" (clamp en 0). */
export function formatCountdown(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const mm = Math.floor(s / 60)
  const ss = s % 60
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

/** Tiempo relativo en español: "hace Xs" / "hace Xm" / "hace Xh". */
export function formatAgo(ts: string | null, now: number = Date.now()): string {
  if (!ts) return '—'
  const then = new Date(ts).getTime()
  if (Number.isNaN(then)) return '—'
  const diff = Math.max(0, Math.floor((now - then) / 1000))
  if (diff < 60) return `hace ${diff}s`
  if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`
  return `hace ${Math.floor(diff / 86400)}d`
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
