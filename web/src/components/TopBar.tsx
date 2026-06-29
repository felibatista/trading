import { useState } from 'react'
import { Power, Settings } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { Status } from '@/lib/types'

const TABS = ['Panel', 'Backtest', 'Historial', 'Config']

function BrandMark() {
  return (
    <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 shadow-sm">
      <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden="true">
        <path
          d="M6 21.5 13 14.5 17.5 19 26 10.5"
          stroke="white"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="26" cy="10.5" r="2.4" fill="white" />
      </svg>
    </span>
  )
}

function StopControl() {
  const [arming, setArming] = useState(false)
  if (arming) {
    // The confirmation step is where stopping is the primary action — so here it
    // gets the loud, high-contrast destructive treatment (Refactoring UI).
    return (
      <div className="flex items-center gap-1.5">
        <Button variant="ghost" size="sm" onClick={() => setArming(false)}>
          Cancelar
        </Button>
        <Button variant="destructive" size="sm" onClick={() => setArming(false)}>
          Confirmar parada
        </Button>
      </div>
    )
  }
  return (
    <Button variant="destructiveQuiet" size="sm" onClick={() => setArming(true)}>
      <Power className="h-3.5 w-3.5" />
      Detener
    </Button>
  )
}

export function TopBar({ status }: { status: Status | null }) {
  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200/80 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <BrandMark />
            <div className="leading-none">
              <div className="font-display text-lg font-bold tracking-tight text-zinc-900">Américo</div>
              <div className="mt-0.5 text-[11px] font-medium text-zinc-500">trading autónomo</div>
            </div>
          </div>
          <nav className="hidden items-center gap-1 md:flex">
            {TABS.map((t, i) => (
              <button
                key={t}
                className={
                  i === 0
                    ? 'rounded-md bg-brand-50 px-3 py-1.5 text-sm font-semibold text-brand-700'
                    : 'rounded-md px-3 py-1.5 text-sm font-medium text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900'
                }
              >
                {t}
              </button>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="flex items-center gap-1.5 rounded-full bg-gain-50 py-1 pl-2 pr-2.5 text-xs font-semibold text-gain-700 ring-1 ring-inset ring-gain-100">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-pulse-live rounded-full bg-gain-500" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-gain-500" />
            </span>
            Operando
          </span>
          {status?.broker_kind === 'paper' && <Badge variant="warning">PAPEL</Badge>}
          <span className="hidden rounded-md bg-zinc-100 px-2.5 py-1 font-mono text-xs font-medium text-zinc-600 sm:inline">
            {status ? `${status.exchange.toUpperCase()} · ${status.timeframe}` : '—'}
          </span>
          <StopControl />
          <Button variant="ghost" size="icon" aria-label="Configuración">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
