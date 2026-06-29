from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from bot.broker.base import Broker
from bot.broker.models import Position
from bot.config import RiskParams, StrategyParams
from bot.data.feed import DataFeed, drop_forming_candle
from bot.models import Action, Signal
from bot.risk.manager import can_open, size_quantity, stop_loss_price, take_profit_price
from bot.store.db import Store
from bot.strategy.ema_rsi import evaluate


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CycleResult:
    symbol: str
    action: str
    detail: str


class Engine:
    def __init__(
        self,
        feed: DataFeed,
        broker: Broker,
        store: Store,
        strategy: StrategyParams,
        risk: RiskParams,
        timeframe: str = "1h",
        limit: int = 200,
        clock: Callable[[], str] = _utcnow,
        log: Callable[[str], None] = print,
        decider: Callable[[pd.DataFrame, StrategyParams], Signal] = evaluate,
    ) -> None:
        self.feed = feed
        self.broker = broker
        self.store = store
        self.strategy = strategy
        self.risk = risk
        self.timeframe = timeframe
        self.limit = limit
        self.clock = clock
        self.log = log
        self.decider = decider

    def _equity(self, prices: dict[str, float]) -> float:
        positions = self.store.get_positions()
        holdings_value = sum(
            p.quantity * prices.get(s, p.entry_price) for s, p in positions.items()
        )
        return self.broker.cash() + holdings_value

    def _snapshot(self, price_by_symbol: dict[str, float], ts: str) -> None:
        equity = self._equity(price_by_symbol)
        self.store.record_equity(ts, equity, self.broker.cash())

    def run_cycle(self, symbol: str) -> CycleResult:
        df = drop_forming_candle(self.feed.fetch_ohlcv(symbol, self.timeframe, self.limit))
        price = float(df["close"].iloc[-1])
        signal = self.decider(df, self.strategy)
        ts = self.clock()
        ind = signal.indicators
        self.store.record_decision(
            ts, symbol, signal.action.value, signal.reason,
            ind.get("ema_fast", float("nan")),
            ind.get("ema_slow", float("nan")),
            ind.get("rsi", float("nan")),
        )

        positions = self.store.get_positions()
        pos = positions.get(symbol)

        # 1) Salida por riesgo (stop-loss / take-profit) antes que la señal.
        if pos is not None and (price <= pos.stop_loss or price >= pos.take_profit):
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(ts, fill)
            self.store.remove_position(symbol)
            reason = "stop-loss" if price <= pos.stop_loss else "take-profit"
            self.log(f"[{symbol}] SALIDA {reason} qty={fill.quantity:.6f} @ {fill.price:.2f}")
            self._snapshot({symbol: price}, ts)
            return CycleResult(symbol, "SELL", f"salida {reason} @ {fill.price:.2f}")

        # 2) Acción de la estrategia.
        detail = signal.reason
        if signal.action is Action.BUY and pos is None:
            equity = self._equity({symbol: price})
            if can_open(len(positions), self.risk):
                qty = size_quantity(equity, price, self.risk)
                if qty > 0:
                    fill = self.broker.buy(symbol, qty, price)
                    self.store.record_fill(ts, fill)
                    new_pos = Position(
                        symbol, fill.quantity, fill.price,
                        stop_loss_price(fill.price, self.risk),
                        take_profit_price(fill.price, self.risk),
                    )
                    self.store.upsert_position(new_pos, ts)
                    detail = f"compra qty={fill.quantity:.6f} @ {fill.price:.2f}"
                    self.log(f"[{symbol}] COMPRA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        elif signal.action is Action.SELL and pos is not None:
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(ts, fill)
            self.store.remove_position(symbol)
            detail = f"venta qty={fill.quantity:.6f} @ {fill.price:.2f}"
            self.log(f"[{symbol}] VENTA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        else:
            self.log(f"[{symbol}] {signal.action.value}: {signal.reason}")

        self._snapshot({symbol: price}, ts)
        return CycleResult(symbol, signal.action.value, detail)
