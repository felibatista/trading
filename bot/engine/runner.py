from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from bot.ai.advisor import AIAdvisor, NoopAdvisor
from bot.broker.base import Broker
from bot.broker.models import Position
from bot.config import RiskParams, StrategyParams
from bot.data.feed import DataFeed, drop_forming_candle
from bot.models import Action, AIContext, AIVerdict, Signal
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
        advisor: AIAdvisor | None = None,
        ai_affects_execution: bool = False,
        account: str = "default",
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
        # Apagado por defecto: NoopAdvisor confirma siempre sin tocar la red.
        self.advisor: AIAdvisor = advisor if advisor is not None else NoopAdvisor()
        # La IA solo puede ALTERAR la ejecución (vetar) en paper; en real es informativa.
        self.ai_affects_execution = ai_affects_execution
        self.account = account

    def _equity(self, prices: dict[str, float]) -> float:
        positions = self.store.get_positions(self.account)
        holdings_value = sum(
            p.quantity * prices.get(s, p.entry_price) for s, p in positions.items()
        )
        return self.broker.cash() + holdings_value

    def _snapshot(self, price_by_symbol: dict[str, float], ts: str) -> None:
        equity = self._equity(price_by_symbol)
        self.store.record_equity(self.account, ts, equity, self.broker.cash())

    def _ai_context(self, symbol: str, signal: Signal, price: float) -> AIContext:
        return AIContext(
            symbol=symbol,
            action=signal.action,
            reason=signal.reason,
            price=price,
            has_position=False,  # solo se consulta cuando no hay posición abierta
            indicators=dict(signal.indicators),
            risk={
                "risk_per_trade": self.risk.risk_per_trade,
                "stop_loss_pct": self.risk.stop_loss_pct,
                "take_profit_pct": self.risk.take_profit_pct,
                "max_exposure_pct": self.risk.max_exposure_pct,
                "max_positions": float(self.risk.max_positions),
            },
        )

    @staticmethod
    def _ai_action(signal: Signal, verdict: AIVerdict | None) -> str | None:
        # La opinión de la IA: mantiene la acción si confirma, o "HOLD" si vetó.
        if verdict is None:
            return None
        return signal.action.value if verdict.confirm else Action.HOLD.value

    def run_cycle(self, symbol: str) -> CycleResult:
        df = drop_forming_candle(self.feed.fetch_ohlcv(symbol, self.timeframe, self.limit))
        price = float(df["close"].iloc[-1])
        signal = self.decider(df, self.strategy)
        ts = self.clock()
        ind = signal.indicators

        positions = self.store.get_positions(self.account)
        pos = positions.get(symbol)

        # Asesor de IA: SOLO revisa ENTRADAS (compras) que de hecho podrían ejecutarse.
        # Nunca se consulta para HOLD, para ventas, ni para cierres por SL/TP.
        verdict: AIVerdict | None = None
        if (
            self.advisor.enabled
            and signal.action is Action.BUY
            and pos is None
            and can_open(len(positions), self.risk)
        ):
            verdict = self.advisor.review(self._ai_context(symbol, signal, price))

        self.store.record_decision(
            self.account, ts, symbol, signal.action.value, signal.reason,
            ind.get("ema_fast", float("nan")),
            ind.get("ema_slow", float("nan")),
            ind.get("rsi", float("nan")),
            ai_action=self._ai_action(signal, verdict),
            ai_confidence=(verdict.confidence if verdict is not None else None),
            ai_rationale=(verdict.rationale if verdict is not None else None),
        )

        # 1) Salida por riesgo (stop-loss / take-profit) antes que la señal. Nunca la veta la IA.
        if pos is not None and (price <= pos.stop_loss or price >= pos.take_profit):
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(self.account, ts, fill)
            self.store.remove_position(self.account, symbol)
            reason = "stop-loss" if price <= pos.stop_loss else "take-profit"
            self.log(f"[{symbol}] SALIDA {reason} qty={fill.quantity:.6f} @ {fill.price:.2f}")
            self._snapshot({symbol: price}, ts)
            return CycleResult(symbol, "SELL", f"salida {reason} @ {fill.price:.2f}")

        # Veto de IA: solo degrada una COMPRA a HOLD, y solo si puede afectar la ejecución (paper).
        vetoed = verdict is not None and not verdict.confirm
        effective_action = signal.action
        if vetoed and self.ai_affects_execution:
            effective_action = Action.HOLD

        # 2) Acción de la estrategia (ya filtrada por la IA en la entrada).
        detail = signal.reason
        if effective_action is Action.BUY and pos is None:
            equity = self._equity({symbol: price})
            if can_open(len(positions), self.risk):
                qty = size_quantity(equity, price, self.risk)
                if qty > 0:
                    fill = self.broker.buy(symbol, qty, price)
                    self.store.record_fill(self.account, ts, fill)
                    new_pos = Position(
                        symbol, fill.quantity, fill.price,
                        stop_loss_price(fill.price, self.risk),
                        take_profit_price(fill.price, self.risk),
                    )
                    self.store.upsert_position(self.account, new_pos, ts)
                    detail = f"compra qty={fill.quantity:.6f} @ {fill.price:.2f}"
                    self.log(f"[{symbol}] COMPRA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        elif signal.action is Action.SELL and pos is not None:
            fill = self.broker.sell(symbol, pos.quantity, price)
            self.store.record_fill(self.account, ts, fill)
            self.store.remove_position(self.account, symbol)
            detail = f"venta qty={fill.quantity:.6f} @ {fill.price:.2f}"
            self.log(f"[{symbol}] VENTA qty={fill.quantity:.6f} @ {fill.price:.2f}")
        elif vetoed and self.ai_affects_execution:
            detail = f"compra vetada por IA: {verdict.rationale}"
            self.log(f"[{symbol}] COMPRA vetada por IA: {verdict.rationale}")
        else:
            self.log(f"[{symbol}] {signal.action.value}: {signal.reason}")

        self._snapshot({symbol: price}, ts)
        return CycleResult(symbol, effective_action.value, detail)

    def run_loop(
        self,
        symbols: list[str],
        interval_seconds: int,
        max_cycles: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> int:
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            for symbol in symbols:
                try:
                    self.run_cycle(symbol)
                except Exception as exc:  # noqa: BLE001 - aislar fallos por símbolo
                    self.log(f"[{symbol}] ERROR: {exc}")
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            sleep(interval_seconds)
        return cycles
