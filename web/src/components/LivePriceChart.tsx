import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardEyebrow, CardHeader } from '@/components/ui/card'
import { Delta } from '@/components/Delta'
import { formatPct, formatUsd } from '@/lib/format'
import { ema } from '@/lib/indicators'
import { tokens } from '@/lib/tokens'
import type { Candle, Fill, Position, Strategy } from '@/lib/types'

function label(ts: string): string {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts.slice(11, 16)
  return d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

/** Índice de la vela que contiene/precede al timestamp del fill. */
function bucketIndex(candleTimes: number[], fillTs: string): number {
  const t = new Date(fillTs).getTime()
  if (Number.isNaN(t)) return -1
  let idx = -1
  for (let i = 0; i < candleTimes.length; i++) {
    if (candleTimes[i] <= t) idx = i
    else break
  }
  return idx
}

interface ChartPoint {
  t: string
  close: number
  emaFast: number
  emaSlow: number
  buy: number | null
  sell: number | null
}

export function LivePriceChart({
  candles,
  fills,
  position,
  strategy,
  symbol,
  timeframe,
}: {
  candles: Candle[]
  fills: Fill[]
  position: Position | null
  strategy: Strategy | null
  symbol: string
  timeframe: string
}) {
  const fast = strategy?.fast ?? 20
  const slow = strategy?.slow ?? 50

  const closes = candles.map((c) => c.close)
  const emaFast = ema(closes, fast)
  const emaSlow = ema(closes, slow)
  const candleTimes = candles.map((c) => new Date(c.ts).getTime())

  const data: ChartPoint[] = candles.map((c, i) => ({
    t: label(c.ts),
    close: c.close,
    emaFast: emaFast[i],
    emaSlow: emaSlow[i],
    buy: null,
    sell: null,
  }))

  // Marcar los fills sobre su vela correspondiente.
  for (const f of fills) {
    if (f.symbol !== symbol) continue
    const idx = bucketIndex(candleTimes, f.ts)
    if (idx < 0 || idx >= data.length) continue
    if (f.side === 'BUY') data[idx].buy = f.price
    else data[idx].sell = f.price
  }

  const last = candles.length ? candles[candles.length - 1] : null
  const prev = candles.length > 1 ? candles[candles.length - 2] : null
  const lastClose = last?.close ?? 0
  const change = last && prev ? last.close - prev.close : 0
  const changePct = prev && prev.close ? change / prev.close : 0

  // Dominio Y incluyendo EMAs, stop y take para que las líneas de referencia se vean.
  const yValues: number[] = []
  for (const p of data) yValues.push(p.close, p.emaFast, p.emaSlow)
  if (position) yValues.push(position.stop_loss, position.take_profit)
  const yMin = yValues.length ? Math.min(...yValues) : 0
  const yMax = yValues.length ? Math.max(...yValues) : 1
  const pad = (yMax - yMin) * 0.05 || yMax * 0.01 || 1
  const domain: [number, number] = [yMin - pad, yMax + pad]

  const fmtPrice = (v: number) => formatUsd(Number(v))

  return (
    <Card className="overflow-hidden">
      {/* Brand accent on the page's hero panel (Refactoring UI: accent borders). */}
      <div className="accent-top h-1 w-full" />
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardEyebrow>
            Precio en vivo · {symbol || '—'} · {timeframe || '—'}
          </CardEyebrow>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-3xl font-semibold tabular-nums text-zinc-900">
              {last ? fmtPrice(lastClose) : '—'}
            </span>
            {last && prev && (
              <Delta
                value={change}
                label={`${formatUsd(Math.abs(change))} (${formatPct(changePct)})`}
                className="text-sm"
              />
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <Badge variant="brand">EMA {fast}</Badge>
          <Badge variant="warning">EMA {slow}</Badge>
          <span className="flex items-center gap-1.5 rounded-full bg-gain-50 px-2.5 py-0.5 text-xs font-semibold text-gain-700 ring-1 ring-inset ring-gain-100">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-pulse-live rounded-full bg-gain-500" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-gain-500" />
            </span>
            EN VIVO
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {candles.length === 0 ? (
          <div className="flex h-72 w-full items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-zinc-50">
            <p className="text-sm text-zinc-500">Esperando datos del mercado…</p>
          </div>
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 12, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke={tokens.grid} vertical={false} />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 11, fill: tokens.axis, fontFamily: 'JetBrains Mono' }}
                  tickLine={false}
                  axisLine={{ stroke: tokens.grid }}
                  minTickGap={28}
                />
                <YAxis
                  domain={domain}
                  tick={{ fontSize: 11, fill: tokens.axis, fontFamily: 'JetBrains Mono' }}
                  tickLine={false}
                  axisLine={false}
                  width={72}
                  tickFormatter={(v) => fmtPrice(Number(v))}
                />
                <Tooltip
                  formatter={(v, name) => [fmtPrice(Number(v)), name]}
                  contentStyle={{
                    borderRadius: 10,
                    border: 'none',
                    boxShadow: '0 14px 24px -10px hsl(222 42% 25% / 0.18)',
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono',
                  }}
                  labelStyle={{ color: tokens.axis, fontFamily: 'Inter' }}
                  cursor={{ stroke: tokens.brand400, strokeWidth: 1, strokeDasharray: '3 3' }}
                />
                {position && (
                  <ReferenceLine
                    y={position.stop_loss}
                    stroke={tokens.loss}
                    strokeDasharray="4 4"
                    label={{ value: 'Stop', position: 'insideTopLeft', fill: tokens.loss, fontSize: 10 }}
                  />
                )}
                {position && (
                  <ReferenceLine
                    y={position.take_profit}
                    stroke={tokens.gain}
                    strokeDasharray="4 4"
                    label={{ value: 'Take', position: 'insideBottomLeft', fill: tokens.gain, fontSize: 10 }}
                  />
                )}
                <Line
                  name="Precio"
                  type="monotone"
                  dataKey="close"
                  stroke={tokens.ink}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  name={`EMA ${fast}`}
                  type="monotone"
                  dataKey="emaFast"
                  stroke={tokens.brand}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  name={`EMA ${slow}`}
                  type="monotone"
                  dataKey="emaSlow"
                  stroke={tokens.warn}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  name="Compra"
                  dataKey="buy"
                  stroke="transparent"
                  connectNulls={false}
                  isAnimationActive={false}
                  dot={{ r: 5, fill: tokens.gain, stroke: '#ffffff', strokeWidth: 1.5 }}
                />
                <Line
                  name="Venta"
                  dataKey="sell"
                  stroke="transparent"
                  connectNulls={false}
                  isAnimationActive={false}
                  dot={{ r: 5, fill: tokens.loss, stroke: '#ffffff', strokeWidth: 1.5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
