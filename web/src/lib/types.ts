export interface Strategy {
  fast: number
  slow: number
  rsi_period: number
  rsi_oversold: number
  rsi_overbought: number
}

export interface Status {
  exchange: string
  timeframe: string
  broker_kind: string
  symbols: string[]
  equity: number
  cash: number
  loop_interval_seconds: number
  last_run_at: string | null
  next_run_at: string | null
  strategy: Strategy
}

export interface Candle {
  ts: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface EquityPoint {
  ts: string
  equity: number
  cash: number
}

export interface Position {
  symbol: string
  quantity: number
  entry_price: number
  stop_loss: number
  take_profit: number
}

export interface Decision {
  ts: string
  symbol: string
  action: string
  reason: string
  // Indicadores EMA/RSI: null cuando la estrategia no los produce (no-ema_rsi).
  ema_fast: number | null
  ema_slow: number | null
  rsi: number | null
  ai_action?: string | null
  ai_confidence?: number | null
  ai_rationale?: string | null
}

export interface Fill {
  ts: string
  symbol: string
  side: string
  quantity: number
  price: number
  fee: number
}

export interface Account {
  id: string
  name: string
  strategy: string
  symbol: string
  timeframe: string
  interval_seconds: number
  ai_enabled: boolean
  ai_provider: string
  ai_model: string
  enabled: boolean
  equity: number
  cash: number
  starting_cash: number
}
