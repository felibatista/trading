import { useCallback, useEffect, useState } from 'react'
import { AlertCircle, Settings } from 'lucide-react'
import { AccountBar } from '@/components/AccountBar'
import { AccountConfig } from '@/components/AccountConfig'
import { BacktestView } from '@/components/BacktestView'
import { ComparisonChart } from '@/components/ComparisonChart'
import { ActivityLog } from '@/components/ActivityLog'
import { EquityChart } from '@/components/EquityChart'
import { HistoryTable } from '@/components/HistoryTable'
import { KpiRow } from '@/components/KpiRow'
import { LiveAnalysis } from '@/components/LiveAnalysis'
import { LivePriceChart } from '@/components/LivePriceChart'
import { NextRunCard } from '@/components/NextRunCard'
import { PositionsTable } from '@/components/PositionsTable'
import { TopBar } from '@/components/TopBar'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const LIVE_INTERVAL = 2500
const SLOW_INTERVAL = 5000

export default function App() {
  const accounts = usePolling(useCallback(() => api.getAccounts(), []), SLOW_INTERVAL)
  const accountList = accounts.data ?? []
  const [account, setAccount] = useState<string | null>(null)
  const [configOpen, setConfigOpen] = useState(false)
  const [view, setView] = useState<'live' | 'backtest'>('live')
  const selectedAccount = accountList.find((a) => a.id === account) ?? null

  // Selección inicial: primera cuenta cuando llega la lista.
  useEffect(() => {
    if (account === null && accountList.length > 0) setAccount(accountList[0].id)
  }, [account, accountList])

  const acc = account ?? undefined

  const status = usePolling(useCallback(() => acc ? api.getStatus(acc) : Promise.resolve(null), [acc]), LIVE_INTERVAL, [account])
  const candles = usePolling(useCallback(() => acc ? api.getCandles(undefined, undefined, 120, acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const decisions = usePolling(useCallback(() => acc ? api.getDecisions(20, acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const positions = usePolling(useCallback(() => acc ? api.getPositions(acc) : Promise.resolve([]), [acc]), LIVE_INTERVAL, [account])
  const equity = usePolling(useCallback(() => acc ? api.getEquity(200, acc) : Promise.resolve([]), [acc]), SLOW_INTERVAL, [account])
  const fills = usePolling(useCallback(() => acc ? api.getFills(50, acc) : Promise.resolve([]), [acc]), SLOW_INTERVAL, [account])

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
      <div className="accent-top h-1 w-full" />
      <TopBar status={status.data} view={view} onNavigate={setView} />
      <main className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
        {status.error && (
          <div className="flex items-start gap-2.5 rounded-lg bg-loss-50 px-4 py-3 text-sm text-loss-700 ring-1 ring-inset ring-loss-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>No se pudo conectar con la API.</span>
          </div>
        )}

        {/* Switch para mobile: el navbar (tabs) está oculto en pantallas chicas. */}
        <div className="flex w-fit gap-1 rounded-lg bg-zinc-100 p-1 text-sm md:hidden">
          <button
            onClick={() => setView('live')}
            className={`rounded-md px-3 py-1 font-medium transition ${
              view === 'live' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'
            }`}
          >
            En vivo
          </button>
          <button
            onClick={() => setView('backtest')}
            className={`rounded-md px-3 py-1 font-medium transition ${
              view === 'backtest' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500 hover:text-zinc-700'
            }`}
          >
            Backtest
          </button>
        </div>

        {view === 'backtest' && <BacktestView />}

        {view === 'live' && (
          <>
        {accountList.length > 0 && (
          <div className="flex items-center justify-between gap-3">
            <AccountBar accounts={accountList} selected={account} onSelect={setAccount} />
            {selectedAccount && (
              <Button variant="outline" size="sm" onClick={() => setConfigOpen(true)}>
                <Settings className="h-4 w-4" /> Config
              </Button>
            )}
          </div>
        )}
        {configOpen && selectedAccount && (
          <AccountConfig
            account={selectedAccount}
            onClose={() => setConfigOpen(false)}
            onSaved={() => {}}
          />
        )}

        {accountList.length > 1 && <ComparisonChart accounts={accountList} />}

        <KpiRow status={status.data} series={series} />

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

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <LiveAnalysis decision={decisionList[0] ?? null} lastClose={lastClose} strategy={strategy} />
          <div className="lg:col-span-2">
            <EquityChart series={series} />
          </div>
        </div>

        <PositionsTable positions={positionList} price={lastClose} />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <HistoryTable fills={fillList} />
          <ActivityLog decisions={decisionList} />
        </div>
          </>
        )}
      </main>
    </div>
  )
}
