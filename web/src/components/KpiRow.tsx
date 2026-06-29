import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatPct, formatUsd, pnlAbsolute, pnlColor, winRate } from '@/lib/format'
import type { EquityPoint, Status } from '@/lib/types'

function todaySeries(series: EquityPoint[]): EquityPoint[] {
  const today = new Date().toISOString().slice(0, 10)
  const filtered = series.filter((p) => p.ts.slice(0, 10) === today)
  return filtered.length >= 2 ? filtered : series
}

export function KpiRow({ status, series }: { status: Status | null; series: EquityPoint[] }) {
  const equity = status?.equity ?? (series.length ? series[series.length - 1].equity : 0)
  const pnlToday = pnlAbsolute(todaySeries(series))
  const pnlTotal = pnlAbsolute(series)
  const base = series.length ? series[0].equity : 0
  const pnlTotalPct = base > 0 ? pnlTotal / base : 0
  const wr = winRate(series)

  const cards = [
    { title: 'Equity', value: formatUsd(equity), delta: null as string | null, color: 'text-zinc-900' },
    { title: 'P&L de hoy', value: formatUsd(pnlToday), delta: null, color: pnlColor(pnlToday) },
    { title: 'P&L total', value: formatUsd(pnlTotal), delta: formatPct(pnlTotalPct), color: pnlColor(pnlTotal) },
    { title: 'Win rate', value: formatPct(wr).replace('+', ''), delta: null, color: 'text-zinc-900' },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.title}>
          <CardHeader className="pb-2">
            <CardTitle>{c.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`font-mono text-2xl font-semibold tabular-nums ${c.color}`}>{c.value}</div>
            {c.delta && <div className={`mt-1 text-xs font-medium ${c.color}`}>{c.delta}</div>}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
