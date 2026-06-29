from __future__ import annotations

import pandas as pd

from bot.backtest.feed import HistoricalFeed
from bot.data.feed import drop_forming_candle


def _df(n: int) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="ms", utc=True),
        "open": closes, "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes], "close": closes, "volume": [1.0] * n,
    })


def test_returns_slice_up_to_cursor():
    feed = HistoricalFeed(_df(10))
    feed.set_cursor(4)
    out = feed.fetch_ohlcv("BTC/USDT", "1m", limit=200)
    assert len(out) == 5
    assert out["close"].iloc[-1] == 104.0  # vela del cursor


def test_respects_limit_tail():
    feed = HistoricalFeed(_df(10))
    feed.set_cursor(8)
    out = feed.fetch_ohlcv("BTC/USDT", "1m", limit=3)
    assert len(out) == 3
    assert list(out["close"]) == [106.0, 107.0, 108.0]


def test_no_look_ahead_forming_candle_semantics():
    # Con cursor en k, tras drop_forming_candle la última vela CERRADA es k-1.
    feed = HistoricalFeed(_df(10))
    feed.set_cursor(5)
    closed = drop_forming_candle(feed.fetch_ohlcv("BTC/USDT", "1m", limit=200))
    assert closed["close"].iloc[-1] == 104.0  # k-1 = 4, nunca la vela 5 "en formación"
