import { LineChart as LineChartIcon } from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardEyebrow, CardHeader } from '@/components/ui/card'
import { Delta } from '@/components/Delta'
import { formatPct, formatUsd } from '@/lib/format'
import { tokens } from '@/lib/tokens'
import type { EquityPoint } from '@/lib/types'

// The hero/thesis of the page: the single number that says "is the bot working",
// the equity curve that backs it up, and the cumulative return stated with a
// direction arrow (not color alone). Equity is drawn in brand indigo so the
// curve never poses as a green/red P&L signal.
export function EquityChart({
  series,
  equity,
  returnPct,
}: {
  series: EquityPoint[]
  equity?: number
  returnPct?: number
}) {
  const data = series.map((p) => ({ t: p.ts.slice(11, 16), equity: p.equity, cash: p.cash }))
  const hasData = data.length > 1
  const latestEquity = equity ?? (series.length ? series[series.length - 1].equity : 0)
  const base = series.length ? series[0].equity : 0
  const ret = returnPct ?? (base > 0 ? latestEquity / base - 1 : 0)

  return (
    <Card>
      <CardHeader>
        <CardEyebrow>Equity actual</CardEyebrow>
        <div className="font-mono text-4xl font-semibold tracking-tight text-zinc-900 tabular-nums">
          {formatUsd(latestEquity)}
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Delta value={ret} label={formatPct(ret)} />
          <span className="text-zinc-400">retorno acumulado</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64 w-full">
          {hasData ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tokens.brand} stopOpacity={0.22} />
                    <stop offset="95%" stopColor={tokens.brand} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke={tokens.grid} vertical={false} />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 11, fill: tokens.axis, fontFamily: 'JetBrains Mono' }}
                  tickLine={false}
                  axisLine={{ stroke: tokens.grid }}
                  minTickGap={28}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: tokens.axis, fontFamily: 'JetBrains Mono' }}
                  tickLine={false}
                  axisLine={false}
                  width={68}
                  tickFormatter={(v) => formatUsd(Number(v))}
                />
                <Tooltip
                  formatter={(v) => [formatUsd(Number(v)), 'Equity']}
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
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke={tokens.brand}
                  strokeWidth={2.5}
                  fill="url(#eq)"
                  dot={false}
                  activeDot={{ r: 4, fill: tokens.brand, stroke: 'white', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <LineChartIcon className="h-8 w-8 text-zinc-300" aria-hidden="true" />
              <p className="text-sm text-zinc-500">Aún no hay suficiente historial de equity.</p>
              <p className="text-xs text-zinc-400">La curva aparecerá tras los primeros ciclos del bot.</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
