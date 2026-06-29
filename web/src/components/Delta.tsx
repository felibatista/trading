import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { trend } from '@/lib/format'

// A change figure that communicates direction with an icon AND color, so the
// meaning survives for colorblind users (Refactoring UI: don't rely on color alone).
export function Delta({
  value,
  label,
  className,
  iconClassName = 'h-3.5 w-3.5',
}: {
  value: number
  label: string
  className?: string
  iconClassName?: string
}) {
  const t = trend(value)
  const tone =
    t > 0 ? 'text-gain-700' : t < 0 ? 'text-loss-600' : 'text-zinc-500'
  const Icon = t > 0 ? ArrowUpRight : t < 0 ? ArrowDownRight : Minus
  const direction = t > 0 ? 'al alza' : t < 0 ? 'a la baja' : 'sin cambio'

  return (
    <span className={cn('inline-flex items-center gap-1 font-mono font-semibold tabular-nums', tone, className)}>
      <Icon className={iconClassName} aria-hidden="true" />
      <span>{label}</span>
      <span className="sr-only">{direction}</span>
    </span>
  )
}
