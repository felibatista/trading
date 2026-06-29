from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from bot.ai.advisor import AIAdvisor
from bot.backtest.data import timeframe_to_ms
from bot.backtest.feed import HistoricalFeed
from bot.backtest.metrics import (
    ClosedTrade,
    closed_trades,
    max_drawdown_pct,
    profit_factor,
    sharpe_ratio,
    total_return_pct,
    win_rate,
)

_YEAR_MS = 365.25 * 86_400_000  # cripto opera 24/7: año calendario para anualizar Sharpe
from bot.broker.paper import LocalPaperBroker
from bot.config import RiskParams
from bot.engine.runner import Engine
from bot.store.db import Store
from bot.strategy.registry import get_strategy

# Estrategia que lleva IA (veto) en el backtest; el resto corre en solo-reglas.
AI_STRATEGY = "price_action"
AI_PROVIDER = "openai"
AI_MODEL = "gpt-4o-mini"


@dataclass
class BacktestResult:
    account_id: str
    name: str
    strategy: str
    ai: bool
    return_pct: float
    max_drawdown_pct: float
    win_rate: float
    num_trades: int
    final_equity: float
    exposure: float
    starting_cash: float
    sharpe: float = 0.0
    profit_factor: float | None = None
    equity_curve: list[dict] = field(default_factory=list)
    trades: list[ClosedTrade] = field(default_factory=list)


def _empty_result(account: dict, ai: bool, cash: float) -> BacktestResult:
    return BacktestResult(
        account_id=account["id"], name=account["name"], strategy=account["strategy"],
        ai=ai, return_pct=0.0, max_drawdown_pct=0.0, win_rate=0.0, num_trades=0,
        final_equity=cash, exposure=0.0, starting_cash=cash,
    )


def run_backtest(
    account: dict,
    candles: pd.DataFrame,
    *,
    risk: RiskParams,
    advisor: AIAdvisor | None = None,
    fee_rate: float = 0.001,
    slippage: float = 0.0005,
    limit: int = 200,
    warmup: int = 200,
) -> BacktestResult:
    """Replaya `candles` por el Engine real (mismo código que en vivo) para una cuenta.

    `warmup` velas iniciales se consumen para calentar indicadores; la ventana operada es
    el resto. El reloj del Engine usa el timestamp de la vela cerrada, así la curva de
    equity queda con tiempos reales del mercado.
    """
    ai = advisor is not None
    cash = float(account["starting_cash"])
    symbol = account["symbol"]
    n = len(candles)
    if n <= warmup + 1:
        return _empty_result(account, ai, cash)

    store = Store(":memory:")
    broker = LocalPaperBroker(cash, fee_rate, slippage)
    feed = HistoricalFeed(candles)
    ts_holder: dict[str, str] = {"ts": ""}
    engine = Engine(
        feed=feed,
        broker=broker,
        store=store,
        strategy=account["params"],
        risk=risk,
        timeframe=account["timeframe"],
        limit=limit,
        clock=lambda: ts_holder["ts"],
        log=lambda *_: None,  # silencio: son miles de ciclos
        decider=get_strategy(account["strategy"]),
        advisor=advisor,
        ai_affects_execution=ai,  # en paper el veto SÍ afecta (para medir su efecto)
        account=account["id"],
    )

    timestamps = candles["timestamp"]
    bars_in_position = 0
    traded_bars = 0
    for k in range(warmup, n):
        feed.set_cursor(k)
        ts_holder["ts"] = timestamps.iloc[k - 1].isoformat()  # vela cerrada que se opera
        engine.run_cycle(symbol)
        traded_bars += 1
        if store.get_positions(account["id"]).get(symbol) is not None:
            bars_in_position += 1

    curve = store.equity_series(account["id"], limit=n)
    fills = list(reversed(store.recent_fills(account["id"], limit=n)))  # ascendente
    # Si queda una posición abierta al final, sintetizamos su cierre al último close
    # (sin fee de salida) para que num_trades/win_rate reconcilien con la equity
    # mark-to-market: con esto sum(pnl) == final_equity - starting_cash siempre.
    open_pos = store.get_positions(account["id"]).get(symbol)
    if open_pos is not None:
        # Precio de marca: la última vela operada es la penúltima del df (la última hace de
        # "vela en formación" y se descarta), igual que el snapshot de equity final.
        mark_close = float(candles["close"].iloc[-2])
        fills.append({
            "side": "SELL", "quantity": open_pos.quantity, "price": mark_close, "fee": 0.0,
        })
    trades = closed_trades(fills)
    final_equity = curve[-1]["equity"] if curve else cash
    store.close()

    return BacktestResult(
        account_id=account["id"],
        name=account["name"],
        strategy=account["strategy"],
        ai=ai,
        return_pct=total_return_pct(curve, cash),
        max_drawdown_pct=max_drawdown_pct(curve),
        win_rate=win_rate(trades),
        num_trades=len(trades),
        final_equity=final_equity,
        exposure=(bars_in_position / traded_bars) if traded_bars else 0.0,
        starting_cash=cash,
        sharpe=sharpe_ratio(curve, _YEAR_MS / timeframe_to_ms(account["timeframe"])),
        profit_factor=profit_factor(trades),
        equity_curve=curve,
        trades=trades,
    )


def _default_advisor_factory(provider: str, model: str, timeout: float, retries: int) -> AIAdvisor:
    # Import perezoso: bot.cli arrastra brokers/feed; solo lo necesitamos si hay IA.
    from bot.cli import make_advisor

    return make_advisor(provider, model, timeout, retries)


def run_fleet_backtest(
    accounts: list[dict],
    candles_by_tf: dict[str, pd.DataFrame],
    *,
    risk: RiskParams,
    fee_rate: float = 0.001,
    slippage: float = 0.0005,
    ai_strategy: str = AI_STRATEGY,
    ai_provider: str = AI_PROVIDER,
    ai_model: str = AI_MODEL,
    timeout_seconds: float = 20.0,
    max_retries: int = 1,
    advisor_factory: Callable[[str, str, float, int], AIAdvisor] | None = None,
) -> list[BacktestResult]:
    """Corre el backtest de varias cuentas. La IA (veto) se aplica SOLO a la estrategia
    `ai_strategy` (default price_action) con `ai_provider`/`ai_model`; el resto en
    solo-reglas. `advisor_factory` es inyectable para tests (stub determinístico)."""
    factory = advisor_factory or _default_advisor_factory
    results: list[BacktestResult] = []
    for acc in accounts:
        advisor = None
        if acc["strategy"] == ai_strategy:
            advisor = factory(ai_provider, ai_model, timeout_seconds, max_retries)
        candles = candles_by_tf.get(acc["timeframe"])
        if candles is None or candles.empty:
            results.append(_empty_result(acc, advisor is not None, float(acc["starting_cash"])))
            continue
        results.append(run_backtest(
            acc, candles, risk=risk, advisor=advisor, fee_rate=fee_rate, slippage=slippage,
        ))
    return results
