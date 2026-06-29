from __future__ import annotations

import pandas as pd

from bot.backtest.data import load_ohlcv_range, timeframe_to_ms


class FakeExchange:
    """Devuelve OHLCV en páginas, como ccxt: filas con ts >= since, hasta `limit`."""

    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = sorted(rows, key=lambda r: r[0])
        self.calls: list[int] = []

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        self.calls.append(since)
        return [r for r in self.rows if r[0] >= since][:limit]


def _rows(n: int, tf_ms: int, start: int = 0) -> list[list[float]]:
    return [[start + i * tf_ms, 100.0, 101.0, 99.0, 100.0 + i, 1.0] for i in range(n)]


def test_timeframe_to_ms():
    assert timeframe_to_ms("1m") == 60_000
    assert timeframe_to_ms("1h") == 3_600_000
    try:
        timeframe_to_ms("7s")
        assert False, "debe rechazar timeframe inválido"
    except ValueError:
        pass


def test_paginates_and_dedupes():
    tf = 60_000
    rows = _rows(500, tf, start=0)  # 500 velas de 1m desde t=0
    ex = FakeExchange(rows)
    # ventana [200*tf, 400*tf) sin warmup para simplificar el conteo
    df = load_ohlcv_range(ex, "BTC/USDT", "1m", 200 * tf, 400 * tf, warmup_bars=0, page_limit=100)
    # recorta a [200, 400) -> 200 velas
    assert len(df) == 200
    assert df["timestamp"].iloc[0] == pd.to_datetime(200 * tf, unit="ms", utc=True)
    assert df["timestamp"].iloc[-1] == pd.to_datetime(399 * tf, unit="ms", utc=True)
    # sin duplicados, ordenado
    assert df["timestamp"].is_monotonic_increasing
    assert df["timestamp"].is_unique
    assert len(ex.calls) >= 2  # paginó


def test_warmup_extends_before_since():
    tf = 60_000
    rows = _rows(500, tf, start=0)
    ex = FakeExchange(rows)
    df = load_ohlcv_range(ex, "BTC/USDT", "1m", 300 * tf, 400 * tf, warmup_bars=50, page_limit=100)
    # arranca 50 velas antes de since (250), termina en 399
    assert df["timestamp"].iloc[0] == pd.to_datetime(250 * tf, unit="ms", utc=True)
    assert df["timestamp"].iloc[-1] == pd.to_datetime(399 * tf, unit="ms", utc=True)


def test_empty_when_no_rows():
    ex = FakeExchange([])
    df = load_ohlcv_range(ex, "BTC/USDT", "1m", 0, 100 * 60_000, warmup_bars=0)
    assert df.empty
