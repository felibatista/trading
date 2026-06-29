import { ArrowDownRight, ArrowUpRight, Bot, Minus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { actionLabel, formatUsd } from '@/lib/format'
import type { Decision, Strategy } from '@/lib/types'

function actionVariant(action: string): 'success' | 'danger' | 'default' {
  if (action === 'BUY') return 'success'
  if (action === 'SELL') return 'danger'
  return 'default'
}

export function LiveAnalysis({
  decision,
  lastClose,
  strategy,
}: {
  decision: Decision | null
  lastClose: number | null
  strategy: Strategy | null
}) {
  const oversold = strategy?.rsi_oversold ?? 30
  const overbought = strategy?.rsi_overbought ?? 70

  let trend: 'up' | 'down' | 'flat' = 'flat'
  if (decision) {
    if (decision.ema_fast > decision.ema_slow) trend = 'up'
    else if (decision.ema_fast < decision.ema_slow) trend = 'down'
  }

  const rsi = decision?.rsi ?? null
  const rsiPct = rsi != null ? Math.max(0, Math.min(100, rsi)) : 0
  let rsiZone: 'oversold' | 'overbought' | 'neutral' = 'neutral'
  if (rsi != null) {
    if (rsi <= oversold) rsiZone = 'oversold'
    else if (rsi >= overbought) rsiZone = 'overbought'
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-zinc-900">Análisis en vivo</CardTitle>
        {decision && (
          <Badge variant={actionVariant(decision.action)} className="text-sm">
            {actionLabel(decision.action)}
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {!decision ? (
          <p className="text-sm text-zinc-400">Esperando el primer análisis…</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
                <p className="text-xs text-zinc-400">Precio actual</p>
                <p className="font-mono text-lg font-semibold tabular-nums text-zinc-900">
                  {lastClose != null ? formatUsd(lastClose) : '—'}
                </p>
              </div>
              <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
                <p className="text-xs text-zinc-400">Tendencia</p>
                <p
                  className={`flex items-center gap-1 text-lg font-semibold ${
                    trend === 'up'
                      ? 'text-emerald-600'
                      : trend === 'down'
                        ? 'text-red-600'
                        : 'text-zinc-500'
                  }`}
                >
                  {trend === 'up' ? (
                    <>
                      <ArrowUpRight className="h-4 w-4" /> Alcista
                    </>
                  ) : trend === 'down' ? (
                    <>
                      <ArrowDownRight className="h-4 w-4" /> Bajista
                    </>
                  ) : (
                    <>
                      <Minus className="h-4 w-4" /> Lateral
                    </>
                  )}
                </p>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400">
                  RSI ({strategy?.rsi_period ?? 14})
                </span>
                <span
                  className={`font-medium tabular-nums ${
                    rsiZone === 'oversold'
                      ? 'text-emerald-600'
                      : rsiZone === 'overbought'
                        ? 'text-red-600'
                        : 'text-zinc-700'
                  }`}
                >
                  {rsi != null ? rsi.toFixed(1) : '—'}
                  {rsiZone === 'oversold' && ' · sobreventa'}
                  {rsiZone === 'overbought' && ' · sobrecompra'}
                </span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-zinc-100">
                <div
                  className="absolute inset-y-0 left-0 bg-emerald-200"
                  style={{ width: `${oversold}%` }}
                />
                <div
                  className="absolute inset-y-0 right-0 bg-red-200"
                  style={{ width: `${100 - overbought}%` }}
                />
                <div
                  className="absolute top-1/2 h-3.5 w-1 -translate-y-1/2 rounded-full bg-zinc-900"
                  style={{ left: `calc(${rsiPct}% - 2px)` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-zinc-400 tabular-nums">
                <span>0</span>
                <span>sobreventa {oversold}</span>
                <span>sobrecompra {overbought}</span>
                <span>100</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">EMA rápida {decision.ema_fast.toFixed(2)}</Badge>
              <Badge variant="outline">EMA lenta {decision.ema_slow.toFixed(2)}</Badge>
            </div>

            <div>
              <p className="text-xs text-zinc-400">Motivo</p>
              <p className="text-sm text-zinc-600">{decision.reason}</p>
            </div>

            {decision.ai_action && (
              <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Bot className="h-4 w-4 text-zinc-500" />
                  <span className="text-xs font-medium text-zinc-500">Veredicto IA</span>
                  <Badge variant={actionVariant(decision.ai_action)}>
                    {actionLabel(decision.ai_action)}
                  </Badge>
                  {decision.ai_confidence != null && (
                    <span className="text-xs tabular-nums text-zinc-400">
                      {(decision.ai_confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                {decision.ai_rationale && (
                  <p className="text-sm text-zinc-600">{decision.ai_rationale}</p>
                )}
              </div>
            )}

            <p className="text-xs text-zinc-300 tabular-nums">{decision.ts}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
