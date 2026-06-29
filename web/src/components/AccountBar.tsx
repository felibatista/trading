import type { Account } from '@/lib/types'
import { formatUsd } from '@/lib/format'

function pnlPct(a: Account): number {
  if (!a.starting_cash) return 0
  return (a.equity / a.starting_cash - 1) * 100
}

export function AccountBar({
  accounts,
  selected,
  onSelect,
}: {
  accounts: Account[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  const ranked = [...accounts].sort((a, b) => pnlPct(b) - pnlPct(a))
  return (
    <div className="flex flex-wrap gap-2">
      {ranked.map((a, i) => {
        const pnl = pnlPct(a)
        const isSel = a.id === selected
        const tone = pnl > 0 ? 'text-gain-700' : pnl < 0 ? 'text-loss-700' : 'text-zinc-500'
        return (
          <button
            key={a.id}
            onClick={() => onSelect(a.id)}
            className={
              'flex min-w-[8.5rem] flex-col items-start rounded-xl border px-3 py-2 text-left transition ' +
              (isSel
                ? 'border-brand-300 bg-brand-50 ring-2 ring-inset ring-brand-200'
                : 'border-zinc-200 bg-white hover:border-zinc-300')
            }
          >
            <div className="flex w-full items-center justify-between gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                #{i + 1}
              </span>
              {a.enabled ? (
                <span className="h-1.5 w-1.5 rounded-full bg-gain-500" aria-label="activa" />
              ) : (
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-300" aria-label="pausada" />
              )}
            </div>
            <span className="font-display text-sm font-semibold text-zinc-900">{a.name}</span>
            <span className="text-[11px] text-zinc-500">{a.strategy}</span>
            <span className={`mt-1 font-mono text-sm font-semibold tabular-nums ${tone}`}>
              {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}%
            </span>
            <span className="font-mono text-[11px] text-zinc-400 tabular-nums">
              {formatUsd(a.equity)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
