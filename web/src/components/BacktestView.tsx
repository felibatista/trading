import { useState } from 'react'
import { Play, Loader2, AlertCircle } from 'lucide-react'
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { fixed, formatUsd } from '@/lib/format'
import type { BacktestResult } from '@/lib/types'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#a855f7']

function isoDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

export function BacktestView() {
  const [from, setFrom] = useState(isoDate(Date.now() - 7 * 86_400_000))
  const [to, setTo] = useState(isoDate(Date.now()))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<BacktestResult[] | null>(null)

  function preset(days: number) {
    setFrom(isoDate(Date.now() - days * 86_400_000))
    setTo(isoDate(Date.now()))
  }

  async function run() {
    setLoading(true)
    setError(null)
    try {
      setResults(await api.runBacktest({ from, to }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const ranked = results ? [...results].sort((a, b) => b.return_pct - a.return_pct) : []

  // Curva de equity por estrategia, alineada por índice (los timeframes difieren),
  // en P&L % sobre el capital inicial de cada cuenta.
  const maxLen = Math.max(0, ...ranked.map((r) => r.equity_curve.length))
  const chartData = Array.from({ length: maxLen }, (_, i) => {
    const row: Record<string, number | null> = { i }
    for (const r of ranked) {
      const pts = r.equity_curve
      const base = pts[0]?.equity || 10000
      row[r.account_id] = pts[i] ? (pts[i].equity / base - 1) * 100 : null
    }
    return row
  })

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-zinc-900">
            Backtest · histórico
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <label className="block text-sm">
              <span className="text-zinc-600">Desde</span>
              <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)}
                     className="mt-1 block rounded-md border border-zinc-200 px-2 py-1.5" />
            </label>
            <label className="block text-sm">
              <span className="text-zinc-600">Hasta</span>
              <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)}
                     className="mt-1 block rounded-md border border-zinc-200 px-2 py-1.5" />
            </label>
            <div className="flex gap-1.5">
              {[7, 14, 30].map((d) => (
                <Button key={d} variant="outline" size="sm" onClick={() => preset(d)}>{d}d</Button>
              ))}
            </div>
            <Button size="sm" onClick={run} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {loading ? 'Corriendo…' : 'Correr backtest'}
            </Button>
          </div>
          <p className="mt-2 text-xs text-zinc-400">
            La IA (veto) se usa solo en <span className="font-medium">price_action</span> (OpenAI
            gpt-4o-mini); el resto corre en solo-reglas. La 1ª corrida baja datos de OKX y puede
            tardar ~30–60s.
          </p>
          {error && (
            <p className="mt-3 flex items-start gap-2 rounded-md bg-loss-50 px-3 py-2 text-sm text-loss-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
            </p>
          )}
        </CardContent>
      </Card>

      {results && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold text-zinc-900">Resultados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-100 text-left text-xs text-zinc-400">
                    <th className="py-2 pr-3 font-medium">Estrategia</th>
                    <th className="py-2 px-3 text-right font-medium">Retorno</th>
                    <th className="py-2 px-3 text-right font-medium">Max DD</th>
                    <th className="py-2 px-3 text-right font-medium">Win</th>
                    <th className="py-2 px-3 text-right font-medium">Trades</th>
                    <th className="py-2 px-3 text-right font-medium">Equity final</th>
                  </tr>
                </thead>
                <tbody>
                  {ranked.map((r) => (
                    <tr key={r.account_id} className="border-b border-zinc-50">
                      <td className="py-2 pr-3">
                        <span className="font-medium text-zinc-700">{r.strategy}</span>
                        {r.ai && <Badge variant="outline" className="ml-2">IA</Badge>}
                      </td>
                      <td className={`py-2 px-3 text-right font-mono tabular-nums ${
                        r.return_pct > 0 ? 'text-gain-700' : r.return_pct < 0 ? 'text-loss-600' : 'text-zinc-500'
                      }`}>
                        {r.return_pct >= 0 ? '+' : ''}{fixed(r.return_pct, 2)}%
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600">
                        {fixed(r.max_drawdown_pct, 2)}%
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600">
                        {fixed(r.win_rate * 100, 1)}%
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-600">
                        {r.num_trades}
                      </td>
                      <td className="py-2 px-3 text-right font-mono tabular-nums text-zinc-700">
                        {formatUsd(r.final_equity)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 h-72 w-full">
              {maxLen === 0 ? (
                <p className="pt-8 text-center text-sm text-zinc-400">Sin datos en la ventana.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f4" />
                    <XAxis dataKey="i" tick={{ fontSize: 11, fill: '#a1a1aa' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#a1a1aa' }} width={48}
                           tickFormatter={(v) => `${Number(v).toFixed(1)}%`} />
                    <Tooltip formatter={(v) => `${Number(v).toFixed(2)}%`} />
                    <Legend />
                    {ranked.map((r, idx) => (
                      <Line key={r.account_id} type="monotone" dataKey={r.account_id} name={r.strategy}
                            stroke={COLORS[idx % COLORS.length]} strokeWidth={2}
                            dot={false} connectNulls isAnimationActive={false} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
