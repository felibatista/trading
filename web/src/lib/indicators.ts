/**
 * Exponential Moving Average estándar (k = 2 / (period + 1)).
 * Devuelve un array alineado 1:1 con `values` (sembrado con el primer valor),
 * apto para superponer como serie sobre el precio.
 */
export function ema(values: number[], period: number): number[] {
  if (values.length === 0) return []
  const k = 2 / (period + 1)
  const out: number[] = [values[0]]
  for (let i = 1; i < values.length; i++) {
    out.push(values[i] * k + out[i - 1] * (1 - k))
  }
  return out
}
