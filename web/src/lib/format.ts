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
