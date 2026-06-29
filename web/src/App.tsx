import { useCallback } from 'react'
import { AlertCircle } from 'lucide-react'
import { ActivityLog } from '@/components/ActivityLog'
import { EquityChart } from '@/components/EquityChart'
import { HistoryTable } from '@/components/HistoryTable'
import { KpiRow } from '@/components/KpiRow'
import { LiveAnalysis } from '@/components/LiveAnalysis'
import { LivePriceChart } from '@/components/LivePriceChart'
import { NextRunCard } from '@/components/NextRunCard'
import { PositionsTable } from '@/components/PositionsTable'
import { TopBar } from '@/components/TopBar'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const LIVE_INTERVAL = 2500
const SLOW_INTERVAL = 5000

export default function App() {
  // Lo "vivo" se actualiza rápido.
  const status = usePolling(useCallback(() => api.getStatus(), []), LIVE_INTERVAL)
  const candles = usePolling(useCallback(() => api.getCandles(undefined, undefined, 120), []), LIVE_INTERVAL)
  const decisions = usePolling(useCallback(() => api.getDecisions(20), []), LIVE_INTERVAL)
  const positions = usePolling(useCallback(() => api.getPositions(), []), LIVE_INTERVAL)
  // Lo histórico se actualiza más lento.
  const equity = usePolling(useCallback(() => api.getEquity(200), []), SLOW_INTERVAL)
  const fills = usePolling(useCallback(() => api.getFills(50), []), SLOW_INTERVAL)

  const series = equity.data ?? []
  const decisionList = decisions.data ?? []
  const candleList = candles.data ?? []
  const positionList = positions.data ?? []
  const fillList = fills.data ?? []

  const symbol = status.data?.symbols?.[0] ?? ''
  const timeframe = status.data?.timeframe ?? ''
  const strategy = status.data?.strategy ?? null
  const openPosition = positionList.find((p) => p.symbol === symbol) ?? positionList[0] ?? null
  const lastClose = candleList.length ? candleList[candleList.length - 1].close : null

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      {/* Brand accent across the very top of the layout (Refactoring UI). */}
      <div className="accent-top h-1 w-full" />
      <TopBar status={status.data} />
      <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
        {status.error && (
          <div className="flex items-start gap-2.5 rounded-lg bg-loss-50 px-4 py-3 text-sm text-loss-700 ring-1 ring-inset ring-loss-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              No se pudo conectar con la API. ¿Está corriendo uvicorn en el puerto 8000?
            </span>
          </div>
        )}
        <KpiRow status={status.data} series={series} />

        {/* Vista en vivo: precio analizado en tiempo real + próxima corrida */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <LivePriceChart
              candles={candleList}
              fills={fillList}
              position={openPosition}
              strategy={strategy}
              symbol={symbol}
              timeframe={timeframe}
            />
          </div>
          <NextRunCard status={status.data} />
        </div>

        {/* Detalle del proceso + evolución del equity */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <LiveAnalysis decision={decisionList[0] ?? null} lastClose={lastClose} strategy={strategy} />
          <div className="lg:col-span-2">
            <EquityChart series={series} />
          </div>
        </div>

        <PositionsTable positions={positionList} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HistoryTable fills={fillList} />
          <ActivityLog decisions={decisionList} />
        </div>
      </main>
    </div>
  )
}
