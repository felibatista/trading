from __future__ import annotations

from typing import Protocol

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def ohlcv_to_df(rows: list[list[float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def drop_forming_candle(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:-1]


class DataFeed(Protocol):
    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> pd.DataFrame: ...


def make_ccxt_exchange(exchange_id: str = "okx"):
    """Construye un exchange de ccxt con rate-limit. Compartido por el feed en vivo y el
    fetch histórico paginado del backtest."""
    import ccxt

    return getattr(ccxt, exchange_id)({"enableRateLimit": True})


class CcxtDataFeed:
    def __init__(self, exchange_id: str = "okx") -> None:
        self._exchange = make_ccxt_exchange(exchange_id)

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 200
    ) -> pd.DataFrame:
        rows = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv_to_df(rows)
