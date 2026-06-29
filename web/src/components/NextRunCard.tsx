import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatAgo, formatCountdown } from '@/lib/format'
import type { Status } from '@/lib/types'

export function NextRunCard({ status }: { status: Status | null }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const nextAt = status?.next_run_at ? new Date(status.next_run_at).getTime() : null
  const remaining = nextAt != null && !Number.isNaN(nextAt) ? (nextAt - now) / 1000 : null
  const analyzing = remaining != null && remaining <= 0
  const interval = status?.loop_interval_seconds ?? null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-semibold text-zinc-900">Próxima corrida</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {remaining == null ? (
          <p className="text-sm text-zinc-400">Sin horario de corrida disponible.</p>
        ) : analyzing ? (
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
            <span className="text-2xl font-semibold text-emerald-600">Analizando…</span>
          </div>
        ) : (
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-3xl font-semibold tabular-nums text-zinc-900">
              {formatCountdown(remaining)}
            </span>
            <span className="text-sm text-zinc-400">mm:ss</span>
          </div>
        )}

        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs text-zinc-400">Última corrida</dt>
            <dd className="font-medium tabular-nums text-zinc-700">
              {formatAgo(status?.last_run_at ?? null, now)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Intervalo</dt>
            <dd className="font-medium tabular-nums text-zinc-700">
              {interval != null ? formatCountdown(interval) : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Timeframe</dt>
            <dd className="font-medium tabular-nums text-zinc-700">{status?.timeframe ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-zinc-400">Mercado</dt>
            <dd className="font-medium tabular-nums text-zinc-700">
              {status ? status.exchange.toUpperCase() : '—'}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  )
}
