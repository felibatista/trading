from __future__ import annotations

from bot.store.db import Store

DEFAULT_ACCOUNTS: list[dict] = [
    {
        "id": "scalper", "name": "Scalper EMA/RSI", "strategy": "ema_rsi",
        "symbol": "BTC/USDT", "timeframe": "1m", "interval_seconds": 12,
        "starting_cash": 10000.0, "ai_enabled": True, "enabled": True,
        "params": {"fast": 2, "slow": 4, "rsi_period": 7,
                   "rsi_oversold": 20.0, "rsi_overbought": 85.0},
    },
    {
        "id": "momentum", "name": "Momentum MACD", "strategy": "macd",
        "symbol": "BTC/USDT", "timeframe": "5m", "interval_seconds": 30,
        "starting_cash": 10000.0, "ai_enabled": True, "enabled": True,
        "params": {"fast": 12, "slow": 26, "signal": 9},
    },
    {
        "id": "reversion", "name": "Reversión Bollinger", "strategy": "bollinger",
        "symbol": "BTC/USDT", "timeframe": "15m", "interval_seconds": 60,
        "starting_cash": 10000.0, "ai_enabled": True, "enabled": True,
        "params": {"period": 20, "num_std": 2.0},
    },
    {
        "id": "ruptura", "name": "Ruptura Donchian", "strategy": "breakout",
        "symbol": "BTC/USDT", "timeframe": "30m", "interval_seconds": 120,
        "starting_cash": 10000.0, "ai_enabled": True, "enabled": True,
        "params": {"lookback": 20},
    },
    {
        "id": "price", "name": "Price Action", "strategy": "price_action",
        "symbol": "BTC/USDT", "timeframe": "1h", "interval_seconds": 180,
        "starting_cash": 10000.0, "ai_enabled": True, "enabled": True,
        "params": {"wick_ratio": 2.0},
    },
]


def seed_default_accounts(store: Store) -> None:
    if store.list_accounts():
        return
    for a in DEFAULT_ACCOUNTS:
        store.upsert_account(
            a["id"], a["name"], a["strategy"], a["symbol"], a["timeframe"],
            a["interval_seconds"], a["starting_cash"], a["ai_enabled"],
            a["enabled"], a["params"],
            a.get("ai_provider", "anthropic"), a.get("ai_model", "claude-haiku-4-5"),
        )
