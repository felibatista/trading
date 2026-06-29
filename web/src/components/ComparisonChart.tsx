import { useCallback } from 'react'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { Account } from '@/lib/types'
import { usePolling } from '@/lib/use-polling'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7']

export function ComparisonChart({ accounts }: { accounts: Account[] }) {
  const ids = accounts.map((a) => a.id)
  const idsKey = ids.join(',')
  const series = usePolling(
    useCallback(() => api.getAllAccountsEquity(ids, 200), [idsKey]),
    5000,
    [idsKey],
  )
  const byId = series.data ?? {}
  const start: Record<string, number> = {}
  accounts.forEach((a) => { start[a.id] = a.starting_cash || 10000 })

  // Alinear por índice de paso: fila i = P&L% de cada cuenta en su i-ésimo punto.
  const maxLen = Math.max(0, ...accounts.map((a) => (byId[a.id]?.length ?? 0)))
  const data = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | null> = { i }
    for (const a of accounts) {
      const pts = byId[a.id]
      row[a.id] = pts && pts[i] ? (pts[i].equity / start[a.id] - 1) * 100 : null
    }
    return row
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold text-zinc-900">
          Comparativa de estrategias · P&amp;L %
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72 w-full">
          {maxLen === 0 ? (
            <p className="pt-8 text-center text-sm text-zinc-400">
              Esperando datos de las cuentas…
            </p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f4" />
                <XAxis dataKey="i" tick={{ fontSize: 11, fill: '#a1a1aa' }} />
                <YAxis tick={{ fontSize: 11, fill: '#a1a1aa' }} width={48}
                       tickFormatter={(v) => `${Number(v).toFixed(1)}%`} />
                <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} />
                <Legend />
                {accounts.map((a, idx) => (
                  <Line key={a.id} type="monotone" dataKey={a.id} name={a.name}
                        stroke={COLORS[idx % COLORS.length]} strokeWidth={2}
                        dot={false} connectNulls isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
