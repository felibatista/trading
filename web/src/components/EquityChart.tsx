import { useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { formatUsd } from '@/lib/format'
import type { EquityPoint } from '@/lib/types'

export function EquityChart({ series }: { series: EquityPoint[] }) {
  const [view, setView] = useState('equity')
  const data = series.map((p) => ({ t: p.ts.slice(11, 16), equity: p.equity, cash: p.cash }))

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-zinc-900">Evolución del equity</CardTitle>
        <Tabs value={view} onValueChange={setView}>
          <TabsList>
            <TabsTrigger value="equity">Equity</TabsTrigger>
            <TabsTrigger value="price">Precio</TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        {view === 'price' && (
          <p className="mb-2 text-xs text-zinc-400">Vista de precio próximamente — mostrando equity.</p>
        )}
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
              <XAxis dataKey="t" tick={{ fontSize: 11, fill: '#a1a1aa' }} />
              <YAxis tick={{ fontSize: 11, fill: '#a1a1aa' }} width={70} tickFormatter={(v) => formatUsd(Number(v))} />
              <Tooltip formatter={(v) => formatUsd(Number(v))} />
              <Area type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} fill="url(#eq)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
