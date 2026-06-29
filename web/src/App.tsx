import { useCallback } from 'react'
import { ActivityLog } from '@/components/ActivityLog'
import { DecisionCard } from '@/components/DecisionCard'
import { EquityChart } from '@/components/EquityChart'
import { HistoryTable } from '@/components/HistoryTable'
import { KpiRow } from '@/components/KpiRow'
import { PositionsTable } from '@/components/PositionsTable'
import { TopBar } from '@/components/TopBar'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const INTERVAL = 5000

export default function App() {
  const status = usePolling(useCallback(() => api.getStatus(), []), INTERVAL)
  const equity = usePolling(useCallback(() => api.getEquity(200), []), INTERVAL)
  const positions = usePolling(useCallback(() => api.getPositions(), []), INTERVAL)
  const decisions = usePolling(useCallback(() => api.getDecisions(20), []), INTERVAL)
  const fills = usePolling(useCallback(() => api.getFills(50), []), INTERVAL)

  const series = equity.data ?? []
  const decisionList = decisions.data ?? []

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      <TopBar status={status.data} />
      <main className="mx-auto max-w-7xl space-y-4 p-6">
        {status.error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            No se pudo conectar con la API. ¿Está corriendo uvicorn en el puerto 8000?
          </div>
        )}
        <KpiRow status={status.data} series={series} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <EquityChart series={series} />
          </div>
          <DecisionCard decision={decisionList[0] ?? null} />
        </div>
        <PositionsTable positions={positions.data ?? []} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HistoryTable fills={fills.data ?? []} />
          <ActivityLog decisions={decisionList} />
        </div>
      </main>
    </div>
  )
}
