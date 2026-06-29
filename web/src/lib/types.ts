export interface Status {
  exchange: string
  timeframe: string
  broker_kind: string
  symbols: string[]
  equity: number
  cash: number
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
  ema_fast: number
  ema_slow: number
  rsi: number
}

export interface Fill {
  ts: string
  symbol: string
  side: string
  quantity: number
  price: number
  fee: number
}
