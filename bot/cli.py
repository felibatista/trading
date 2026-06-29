from __future__ import annotations

import argparse
import os

from bot.broker.base import Broker
from bot.broker.okx_demo import OkxDemoBroker
from bot.broker.paper import LocalPaperBroker
from bot.config import Config, load_config
from bot.data.feed import CcxtDataFeed, DataFeed, drop_forming_candle
from bot.engine.runner import Engine
from bot.models import Signal
from bot.store.db import Store
from bot.strategy.ema_rsi import evaluate


def run_decide(
    feed: DataFeed, config: Config, symbol: str, timeframe: str, limit: int = 200
) -> Signal:
    df = drop_forming_candle(feed.fetch_ohlcv(symbol, timeframe, limit))
    return evaluate(df, config.strategy)


def build_broker(config: Config, store: Store | None = None) -> Broker:
    bp = config.broker
    if bp.kind == "okx_demo":
        return OkxDemoBroker(
            os.environ["OKX_API_KEY"],
            os.environ["OKX_API_SECRET"],
            os.environ["OKX_API_PASSWORD"],
        )
    if bp.kind != "paper":
        raise ValueError(f"Broker desconocido: {bp.kind!r}")
    cash = bp.paper_cash
    holdings: dict[str, float] | None = None
    if store is not None:
        eq = store.latest_equity()
        if eq is not None:
            cash = eq[1]
        positions = store.get_positions()
        if positions:
            holdings = {sym: p.quantity for sym, p in positions.items()}
    return LocalPaperBroker(cash, bp.fee_rate, bp.slippage, holdings=holdings)


def _cmd_decide(args) -> int:
    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe
    feed = CcxtDataFeed(exchange)
    signal = run_decide(feed, config, args.symbol, timeframe, config.limit)
    print(f"[{args.symbol} · {timeframe} · {exchange}]")
    print(f"Decisión: {signal.action.value}")
    print(f"Motivo:   {signal.reason}")
    ind = signal.indicators
    print(
        f"EMA fast: {ind['ema_fast']:.2f}  "
        f"EMA slow: {ind['ema_slow']:.2f}  "
        f"RSI: {ind['rsi']:.1f}"
    )
    return 0


def _cmd_run(args) -> int:
    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe
    store = Store(config.db_path)
    engine = Engine(
        feed=CcxtDataFeed(exchange),
        broker=build_broker(config, store),
        store=store,
        strategy=config.strategy,
        risk=config.risk,
        timeframe=timeframe,
        limit=config.limit,
    )
    if args.loop:
        print(f"Loop cada {config.loop_interval_seconds}s · {config.broker.kind} · {exchange}")
        engine.run_loop([args.symbol], config.loop_interval_seconds)
        return 0
    try:
        result = engine.run_cycle(args.symbol)
        print(f"[{result.symbol}] {result.action}: {result.detail}")
    except Exception as exc:  # noqa: BLE001 - mostrar error limpio en vez de traceback
        print(f"Error en el ciclo: {exc}")
        return 1
    return 0


def _cmd_status(args) -> int:
    config = load_config(args.config)
    store = Store(config.db_path)
    eq = store.latest_equity()
    if eq is None:
        print("Sin corridas todavía. Ejecutá: python -m bot run BTC/USDT")
        return 0
    equity, cash = eq
    print(f"Equity: {equity:.2f}  ·  Caja: {cash:.2f}")
    positions = store.get_positions()
    print(f"Posiciones abiertas: {len(positions)}")
    for sym, p in positions.items():
        print(
            f"  {sym}: qty={p.quantity:.6f} entrada={p.entry_price:.2f} "
            f"SL={p.stop_loss:.2f} TP={p.take_profit:.2f}"
        )
    print("Últimas decisiones:")
    for d in store.recent_decisions(limit=5):
        print(f"  {d['ts']} {d['symbol']} {d['action']} — {d['reason']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide", help="Muestra la decisión (sin operar)")
    d.add_argument("symbol")
    d.add_argument("--timeframe", default=None)
    d.add_argument("--exchange", default=None)
    d.add_argument("--config", default="config.yaml")
    d.set_defaults(func=_cmd_decide)

    r = sub.add_parser("run", help="Corre un ciclo (o un loop con --loop) y opera en paper")
    r.add_argument("symbol")
    r.add_argument("--timeframe", default=None)
    r.add_argument("--exchange", default=None)
    r.add_argument("--loop", action="store_true")
    r.add_argument("--config", default="config.yaml")
    r.set_defaults(func=_cmd_run)

    s = sub.add_parser("status", help="Muestra equity, posiciones y últimas decisiones")
    s.add_argument("--config", default="config.yaml")
    s.set_defaults(func=_cmd_status)

    args = parser.parse_args(argv)
    return args.func(args)
