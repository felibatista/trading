from __future__ import annotations

import pandas as pd

from bot.data.feed import DataFeed


class HistoricalFeed(DataFeed):
    """Feed de replay sobre un DataFrame OHLCV ya cargado. Expone `fetch_ohlcv` igual que
    el feed en vivo, devolviendo solo las velas hasta el cursor → permite reusar el
    `Engine` tal cual, sin look-ahead.

    Semántica de "vela en formación": el `Engine` hace `drop_forming_candle` (descarta la
    última fila). Entrega `df[: cursor + 1]`, así la vela del cursor hace de vela en
    formación (se descarta) y la decisión/precio salen de la vela cerrada `cursor - 1`,
    idéntico al comportamiento en vivo.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df.reset_index(drop=True)
        self._cursor = len(self._df) - 1

    def __len__(self) -> int:
        return len(self._df)

    def set_cursor(self, cursor: int) -> None:
        self._cursor = cursor

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 200) -> pd.DataFrame:
        window = self._df.iloc[: self._cursor + 1]
        if limit is not None and limit > 0:
            window = window.tail(limit)
        return window.reset_index(drop=True)
