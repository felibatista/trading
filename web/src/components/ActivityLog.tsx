import { Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actionLabel } from '@/lib/format'
import type { Decision } from '@/lib/types'

function dot(action: string): string {
  if (action === 'BUY') return 'bg-gain-500'
  if (action === 'SELL') return 'bg-loss-500'
  return 'bg-zinc-300'
}

export function ActivityLog({ decisions }: { decisions: Decision[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Actividad reciente</CardTitle>
      </CardHeader>
      <CardContent>
        {decisions.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <Activity className="h-7 w-7 text-zinc-300" aria-hidden="true" />
            <p className="text-sm font-medium text-zinc-600">Sin actividad todavía</p>
            <p className="text-xs text-zinc-400">Cada decisión del bot quedará registrada aquí.</p>
          </div>
        ) : (
          <ul className="space-y-3.5">
            {decisions.map((d, i) => (
              <li key={`${d.ts}-${i}`} className="flex items-start gap-3">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot(d.action)}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-900">{actionLabel(d.action)}</span>
                    <span className="font-mono text-xs text-zinc-400">{d.symbol}</span>
                  </div>
                  <p className="truncate text-xs text-zinc-500">{d.reason}</p>
                  <p className="font-mono text-[11px] tabular-nums text-zinc-400">
                    {d.ts.slice(0, 16).replace('T', ' ')}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
