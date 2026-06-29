import type { ReactNode } from 'react'
import { Card, CardContent, CardEyebrow } from '@/components/ui/card'
import { Delta } from '@/components/Delta'
import { formatPct, formatUsd, pnlAbsolute, winRate } from '@/lib/format'
import type { EquityPoint, Status } from '@/lib/types'

function todaySeries(series: EquityPoint[]): EquityPoint[] {
  const today = new Date().toISOString().slice(0, 10)
  const filtered = series.filter((p) => p.ts.slice(0, 10) === today)
  return filtered.length >= 2 ? filtered : series
}

// A KPI is a label + a number, and the number is the hero: big, monospace,
// tabular. Labels are quiet eyebrows; changes carry an arrow, never color alone.
function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Card>
      <CardContent className="p-5">
        <CardEyebrow>{label}</CardEyebrow>
        <div className="mt-2">{children}</div>
      </CardContent>
    </Card>
  )
}

export function KpiRow({ status, series }: { status: Status | null; series: EquityPoint[] }) {
  const equity = status?.equity ?? (series.length ? series[series.length - 1].equity : 0)
  const pnlToday = pnlAbsolute(todaySeries(series))
  const pnlTotal = pnlAbsolute(series)
  const base = series.length ? series[0].equity : 0
  const pnlTotalPct = base > 0 ? pnlTotal / base : 0
  const wr = winRate(series)

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Stat label="Equity">
        <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-900">{formatUsd(equity)}</div>
      </Stat>
      <Stat label="P&L de hoy">
        <Delta value={pnlToday} label={formatUsd(pnlToday)} className="text-2xl" iconClassName="h-5 w-5" />
      </Stat>
      <Stat label="P&L total">
        <Delta value={pnlTotal} label={formatUsd(pnlTotal)} className="text-2xl" iconClassName="h-5 w-5" />
        <div className="mt-1 font-mono text-xs font-medium tabular-nums text-zinc-500">{formatPct(pnlTotalPct)}</div>
      </Stat>
      <Stat label="Win rate">
        <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-900">
          {formatPct(wr).replace('+', '')}
        </div>
      </Stat>
    </div>
  )
}
