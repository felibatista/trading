import { useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { Account } from '@/lib/types'

const STRATS = ['ema_rsi', 'macd', 'bollinger', 'breakout', 'price_action']
const TFS = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']

export function AccountConfig({
  account, onClose, onSaved,
}: {
  account: Account
  onClose: () => void
  onSaved: () => void
}) {
  const [enabled, setEnabled] = useState(account.enabled)
  const [aiEnabled, setAiEnabled] = useState(account.ai_enabled)
  const [strategy, setStrategy] = useState(account.strategy)
  const [timeframe, setTimeframe] = useState(account.timeframe)
  const [interval, setIntervalS] = useState(account.interval_seconds)
  const [paramsText, setParamsText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // params actuales no vienen en Account; se editan como JSON (vacío = no cambiar).
  async function save() {
    setError(null)
    const patch: Record<string, unknown> = {
      enabled, ai_enabled: aiEnabled, strategy, timeframe, interval_seconds: Number(interval),
    }
    if (paramsText.trim()) {
      try { patch.params = JSON.parse(paramsText) } catch { setError('params: JSON inválido'); return }
    }
    setSaving(true)
    try {
      await api.updateAccount(account.id, patch)
      onSaved()
      onClose()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-zinc-900">Config · {account.name}</h2>
          <button onClick={onClose} aria-label="Cerrar" className="text-zinc-400 hover:text-zinc-700">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 text-sm">
          <label className="flex items-center justify-between">
            <span className="text-zinc-600">Activa</span>
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-zinc-600">IA (veto de entradas)</span>
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} />
          </label>
          <label className="block">
            <span className="text-zinc-600">Estrategia</span>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
                    className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5">
              {STRATS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-600">Timeframe</span>
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}
                    className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5">
              {TFS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-600">Intervalo (segundos)</span>
            <input type="number" min={5} value={interval}
                   onChange={(e) => setIntervalS(Number(e.target.value))}
                   className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5 tabular-nums" />
          </label>
          <label className="block">
            <span className="text-zinc-600">Params (JSON, vacío = no cambiar)</span>
            <textarea value={paramsText} onChange={(e) => setParamsText(e.target.value)}
                      placeholder='{"fast": 2, "slow": 4}' rows={3}
                      className="mt-1 w-full rounded-md border border-zinc-200 px-2 py-1.5 font-mono text-xs" />
          </label>
          {error && <p className="rounded-md bg-loss-50 px-3 py-2 text-loss-700">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" onClick={save} disabled={saving}>{saving ? 'Guardando…' : 'Guardar'}</Button>
        </div>
      </div>
    </div>
  )
}
