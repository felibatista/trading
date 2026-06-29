import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actionLabel } from '@/lib/format'
import type { Decision } from '@/lib/types'

function actionVariant(action: string): 'success' | 'danger' | 'default' {
  if (action === 'BUY') return 'success'
  if (action === 'SELL') return 'danger'
  return 'default'
}

export function DecisionCard({ decision }: { decision: Decision | null }) {
  const [ia, setIa] = useState(false)
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-zinc-900">Decisión de Américo</CardTitle>
        <button
          onClick={() => setIa((v) => !v)}
          className={
            ia
              ? 'rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700'
              : 'rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-500'
          }
        >
          IA {ia ? 'ON' : 'OFF'}
        </button>
      </CardHeader>
      <CardContent>
        {decision ? (
          <div className="space-y-3">
            <Badge variant={actionVariant(decision.action)} className="text-sm">
              {actionLabel(decision.action)}
            </Badge>
            <p className="text-sm text-zinc-600">{decision.reason}</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">RSI {decision.rsi.toFixed(1)}</Badge>
              <Badge variant="outline">EMA rápida {decision.ema_fast.toFixed(2)}</Badge>
              <Badge variant="outline">EMA lenta {decision.ema_slow.toFixed(2)}</Badge>
            </div>
            <p className="text-xs text-zinc-400 tabular-nums">{decision.ts}</p>
          </div>
        ) : (
          <p className="text-sm text-zinc-400">Sin decisiones todavía.</p>
        )}
      </CardContent>
    </Card>
  )
}
