import { describe, expect, it } from 'vitest'
import {
  actionLabel,
  formatAgo,
  formatCountdown,
  formatPct,
  formatUsd,
  pnlAbsolute,
  pnlColor,
  winRate,
} from './format'

describe('formatUsd', () => {
  it('formatea con símbolo y 2 decimales', () => {
    expect(formatUsd(10000)).toBe('$10,000.00')
    expect(formatUsd(1234.5)).toBe('$1,234.50')
  })
})

describe('formatPct', () => {
  it('agrega signo y porcentaje', () => {
    expect(formatPct(0.0123)).toBe('+1.23%')
    expect(formatPct(-0.05)).toBe('-5.00%')
    expect(formatPct(0)).toBe('0.00%')
  })
})

describe('pnlColor', () => {
  it('verde / rojo / neutro según el signo', () => {
    expect(pnlColor(1)).toBe('text-gain-700')
    expect(pnlColor(-1)).toBe('text-loss-600')
    expect(pnlColor(0)).toBe('text-zinc-500')
  })
})

describe('actionLabel', () => {
  it('traduce las acciones al español', () => {
    expect(actionLabel('BUY')).toBe('COMPRAR')
    expect(actionLabel('SELL')).toBe('VENDER')
    expect(actionLabel('HOLD')).toBe('MANTENER')
    expect(actionLabel('OTRA')).toBe('OTRA')
  })
})

describe('formatCountdown', () => {
  it('formatea segundos como mm:ss', () => {
    expect(formatCountdown(0)).toBe('00:00')
    expect(formatCountdown(5)).toBe('00:05')
    expect(formatCountdown(65)).toBe('01:05')
    expect(formatCountdown(3661)).toBe('61:01')
  })
  it('hace clamp de negativos en 00:00', () => {
    expect(formatCountdown(-10)).toBe('00:00')
  })
})

describe('formatAgo', () => {
  const now = Date.parse('2026-06-29T12:00:00Z')
  it('devuelve — sin timestamp', () => {
    expect(formatAgo(null, now)).toBe('—')
  })
  it('segundos / minutos / horas', () => {
    expect(formatAgo('2026-06-29T11:59:30Z', now)).toBe('hace 30s')
    expect(formatAgo('2026-06-29T11:55:00Z', now)).toBe('hace 5m')
    expect(formatAgo('2026-06-29T10:00:00Z', now)).toBe('hace 2h')
  })
})

describe('pnlAbsolute', () => {
  it('último menos primero; 0 con menos de 2 puntos', () => {
    expect(pnlAbsolute([])).toBe(0)
    expect(pnlAbsolute([{ ts: 't', equity: 100, cash: 0 }])).toBe(0)
    expect(
      pnlAbsolute([
        { ts: 't1', equity: 100, cash: 0 },
        { ts: 't2', equity: 130, cash: 0 },
      ]),
    ).toBe(30)
  })
})

describe('winRate', () => {
  it('fracción de variaciones positivas de equity', () => {
    expect(winRate([])).toBe(0)
    expect(
      winRate([
        { ts: 't1', equity: 100, cash: 0 },
        { ts: 't2', equity: 110, cash: 0 },
        { ts: 't3', equity: 105, cash: 0 },
        { ts: 't4', equity: 120, cash: 0 },
      ]),
    ).toBeCloseTo(2 / 3)
  })
})
