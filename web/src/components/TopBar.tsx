import { Settings } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Status } from '@/lib/types'

const TABS = ['Panel', 'Backtest', 'Historial', 'Config']

export function TopBar({ status }: { status: Status | null }) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-emerald-500" />
          <span className="text-lg font-semibold text-zinc-900">Américo</span>
        </div>
        <nav className="flex items-center gap-1">
          {TABS.map((t, i) => (
            <button
              key={t}
              className={
                i === 0
                  ? 'rounded-md bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-900'
                  : 'rounded-md px-3 py-1.5 text-sm text-zinc-500 hover:text-zinc-900'
              }
            >
              {t}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="success">Operando</Badge>
        {status?.broker_kind === 'paper' && <Badge variant="warning">PAPER</Badge>}
        <span className="rounded-md border border-zinc-200 px-3 py-1.5 text-sm text-zinc-600 tabular-nums">
          {status ? `${status.exchange.toUpperCase()} · ${status.timeframe}` : '—'}
        </span>
        <Button variant="destructive" size="sm">
          Detener
        </Button>
        <Button variant="ghost" size="icon" aria-label="Configuración">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
