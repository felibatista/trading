from __future__ import annotations

import argparse

from bot.config import Config, load_config
from bot.data.feed import CcxtDataFeed, DataFeed
from bot.models import Signal
from bot.strategy.ema_rsi import evaluate


def run_decide(
    feed: DataFeed, config: Config, symbol: str, timeframe: str, limit: int = 200
) -> Signal:
    df = feed.fetch_ohlcv(symbol, timeframe, limit)
    return evaluate(df, config.strategy)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bot")
    sub = parser.add_subparsers(dest="command", required=True)
    decide_cmd = sub.add_parser("decide", help="Evalúa la estrategia y muestra la decisión")
    decide_cmd.add_argument("symbol", help="Par, ej. BTC/USDT")
    decide_cmd.add_argument("--timeframe", default=None)
    decide_cmd.add_argument("--exchange", default=None)
    decide_cmd.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    exchange = args.exchange or config.exchange
    timeframe = args.timeframe or config.timeframe

    feed = CcxtDataFeed(exchange)
    signal = run_decide(feed, config, args.symbol, timeframe)

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
