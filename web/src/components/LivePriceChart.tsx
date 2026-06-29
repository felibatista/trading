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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatPct, formatUsd, pnlColor } from '@/lib/format'
import { ema } from '@/lib/indicators'
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
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold text-zinc-900">
            Precio en vivo · {symbol || '—'} · {timeframe || '—'}
          </CardTitle>
          <div className="flex items-center gap-3">
            <span className="font-mono text-2xl font-semibold tabular-nums text-zinc-900">
              {last ? fmtPrice(lastClose) : '—'}
            </span>
            {last && prev && (
              <span className={`text-sm font-medium tabular-nums ${pnlColor(change)}`}>
                {change >= 0 ? '▲' : '▼'} {formatUsd(Math.abs(change))} ({formatPct(changePct)})
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <Badge variant="outline">EMA {fast}</Badge>
          <Badge variant="outline">EMA {slow}</Badge>
          <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            EN VIVO
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {candles.length === 0 ? (
          <div className="flex h-72 w-full items-center justify-center rounded-lg border border-dashed border-zinc-200 bg-zinc-50">
            <p className="text-sm text-zinc-400">Esperando datos del mercado…</p>
          </div>
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 12, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 11, fill: '#a1a1aa' }}
                  minTickGap={28}
                />
                <YAxis
                  domain={domain}
                  tick={{ fontSize: 11, fill: '#a1a1aa' }}
                  width={72}
                  tickFormatter={(v) => fmtPrice(Number(v))}
                />
                <Tooltip
                  formatter={(v, name) => [fmtPrice(Number(v)), name]}
                  labelClassName="text-xs"
                  contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: '#e4e4e7' }}
                />
                {position && (
                  <ReferenceLine
                    y={position.stop_loss}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{ value: 'Stop', position: 'insideTopLeft', fill: '#ef4444', fontSize: 10 }}
                  />
                )}
                {position && (
                  <ReferenceLine
                    y={position.take_profit}
                    stroke="#10b981"
                    strokeDasharray="4 4"
                    label={{ value: 'Take', position: 'insideBottomLeft', fill: '#10b981', fontSize: 10 }}
                  />
                )}
                <Line
                  name="Precio"
                  type="monotone"
                  dataKey="close"
                  stroke="#18181b"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  name={`EMA ${fast}`}
                  type="monotone"
                  dataKey="emaFast"
                  stroke="#3b82f6"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  name={`EMA ${slow}`}
                  type="monotone"
                  dataKey="emaSlow"
                  stroke="#f59e0b"
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
                  dot={{ r: 5, fill: '#10b981', stroke: '#ffffff', strokeWidth: 1.5 }}
                />
                <Line
                  name="Venta"
                  dataKey="sell"
                  stroke="transparent"
                  connectNulls={false}
                  isAnimationActive={false}
                  dot={{ r: 5, fill: '#ef4444', stroke: '#ffffff', strokeWidth: 1.5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
