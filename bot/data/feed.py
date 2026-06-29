from __future__ import annotations

from typing import Protocol

import pandas as pd

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def ohlcv_to_df(rows: list[list[float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=OHLCV_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


class DataFeed(Protocol):
    def fetch_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> pd.DataFrame: ...


class CcxtDataFeed:
    def __init__(self, exchange_id: str = "okx") -> None:
        import ccxt

        self._exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 200
    ) -> pd.DataFrame:
        rows = self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return ohlcv_to_df(rows)
