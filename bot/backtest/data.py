from __future__ import annotations

import pandas as pd

from bot.data.feed import ohlcv_to_df

# Milisegundos por timeframe (mismos que acepta el panel/CLI).
_TF_MS: dict[str, int] = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "1d": 86_400_000,
}


def timeframe_to_ms(timeframe: str) -> int:
    if timeframe not in _TF_MS:
        raise ValueError(f"timeframe no soportado: {timeframe!r}")
    return _TF_MS[timeframe]


def load_ohlcv_range(
    exchange,
    symbol: str,
    timeframe: str,
    since_ms: int,
    until_ms: int,
    *,
    warmup_bars: int = 200,
    page_limit: int = 300,
    max_pages: int = 2000,
) -> pd.DataFrame:
    """Baja OHLCV de `since_ms` a `until_ms` (exclusivo) paginando `fetch_ohlcv` de ccxt.

    Pide `warmup_bars` velas extra ANTES de `since_ms` para que los indicadores estén
    calientes en la primera vela operable. Dedup por timestamp, orden ascendente, recorta
    al rango. `exchange` solo necesita `fetch_ohlcv(symbol, timeframe, since, limit)`.
    """
    tf_ms = timeframe_to_ms(timeframe)
    cursor = since_ms - warmup_bars * tf_ms
    rows: list[list[float]] = []
    pages = 0
    while cursor < until_ms and pages < max_pages:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=page_limit)
        pages += 1
        if not batch:
            break
        rows.extend(batch)
        next_cursor = batch[-1][0] + tf_ms
        if next_cursor <= cursor:  # el exchange no avanzó: corta para no loopear
            break
        cursor = next_cursor
        if len(batch) < page_limit:  # no hay más historia disponible
            break

    df = ohlcv_to_df(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    until_ts = pd.to_datetime(until_ms, unit="ms", utc=True)
    return df[df["timestamp"] < until_ts].reset_index(drop=True)
