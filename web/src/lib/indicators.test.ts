import { describe, expect, it } from 'vitest'
import { ema } from './indicators'

describe('ema', () => {
  it('devuelve [] para entrada vacía', () => {
    expect(ema([], 10)).toEqual([])
  })

  it('siembra con el primer valor y queda alineado 1:1', () => {
    const out = ema([10, 20, 30], 2)
    expect(out).toHaveLength(3)
    expect(out[0]).toBe(10)
  })

  it('aplica k = 2/(period+1)', () => {
    // period=2 -> k = 2/3
    // out[1] = 20 * 2/3 + 10 * 1/3 = 16.6667
    const out = ema([10, 20], 2)
    expect(out[1]).toBeCloseTo(50 / 3)
  })

  it('una serie constante se mantiene constante', () => {
    expect(ema([5, 5, 5, 5], 3)).toEqual([5, 5, 5, 5])
  })
})
