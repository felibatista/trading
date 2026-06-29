from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import app, get_candle_feed, set_candle_feed
from api.deps import get_config, get_store
from bot.config import BrokerParams, Config, StrategyParams
from bot.store.db import Store


class FakeFeed:
    """Feed falso: no toca la red, registra cómo fue llamado."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_symbol: str | None = None
        self.last_timeframe: str | None = None
        self.last_limit: int | None = None

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 200
    ) -> pd.DataFrame:
        self.calls += 1
        self.last_symbol = symbol
        self.last_timeframe = timeframe
        self.last_limit = limit
        ts = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
        return pd.DataFrame(
            {
                "timestamp": ts,
                "open": [1.0, 2.0, 3.0],
                "high": [1.5, 2.5, 3.5],
                "low": [0.5, 1.5, 2.5],
                "close": [1.2, 2.2, 3.2],
                "volume": [10.0, 11.0, 12.0],
            }
        )


class BoomFeed:
    """Simula un fallo de red/exchange."""

    def fetch_ohlcv(self, *args, **kwargs) -> pd.DataFrame:
        raise RuntimeError("network down")


@pytest.fixture
def env():
    store = Store(":memory:")
    cfg = Config(
        exchange="okx",
        timeframe="1h",
        symbols=["ETH/USDT", "BTC/USDT"],
        loop_interval_seconds=3600,
        strategy=StrategyParams(
            fast=9, slow=21, rsi_period=7, rsi_oversold=25.0, rsi_overbought=75.0
        ),
        broker=BrokerParams(kind="paper"),
    )
    feed = FakeFeed()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_config] = lambda: cfg
    app.dependency_overrides[get_candle_feed] = lambda: feed
    set_candle_feed(None)  # limpia el cache de velas en proceso
    client = TestClient(app)
    try:
        yield client, store, feed, cfg
    finally:
        app.dependency_overrides.clear()
        set_candle_feed(None)
        store.close()


# --------------------------- /api/status ---------------------------


def test_status_live_fields_with_decision(env):
    client, store, _feed, _cfg = env
    store.record_decision(
        "2024-01-01T01:00:00+00:00", "BTC/USDT", "BUY", "cruce", 30.5, 29.0, 41.0
    )
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    # campos existentes preservados
    assert body["exchange"] == "okx"
    assert body["timeframe"] == "1h"
    assert body["broker_kind"] == "paper"
    assert body["symbols"] == ["ETH/USDT", "BTC/USDT"]
    # campos nuevos
    assert body["loop_interval_seconds"] == 3600
    assert body["last_run_at"] == "2024-01-01T01:00:00+00:00"
    assert body["next_run_at"] == "2024-01-01T02:00:00+00:00"
    assert body["strategy"] == {
        "fast": 9,
        "slow": 21,
        "rsi_period": 7,
        "rsi_oversold": 25.0,
        "rsi_overbought": 75.0,
    }


def test_status_live_fields_without_decision(env):
    client, _store, _feed, _cfg = env
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["last_run_at"] is None
    assert body["next_run_at"] is None
    assert body["loop_interval_seconds"] == 3600
    assert body["strategy"]["fast"] == 9


# --------------------------- /api/candles ---------------------------


def test_candles_shape_and_includes_forming_candle(env):
    client, _store, _feed, _cfg = env
    r = client.get("/api/candles")
    assert r.status_code == 200
    rows = r.json()
    # devuelve TODAS las velas, incluida la última en formación
    assert len(rows) == 3
    assert set(rows[0]) == {"ts", "open", "high", "low", "close", "volume"}
    assert rows[0]["ts"] == "2024-01-01T00:00:00+00:00"
    assert rows[-1]["close"] == 3.2
    assert rows[-1]["volume"] == 12.0


def test_candles_uses_config_defaults(env):
    client, _store, feed, _cfg = env
    client.get("/api/candles")
    assert feed.last_symbol == "ETH/USDT"  # config.symbols[0]
    assert feed.last_timeframe == "1h"  # config.timeframe
    assert feed.last_limit == 120  # default


def test_candles_respects_query_params(env):
    client, _store, feed, _cfg = env
    client.get("/api/candles?symbol=BTC/USDT&timeframe=15m&limit=50")
    assert feed.last_symbol == "BTC/USDT"
    assert feed.last_timeframe == "15m"
    assert feed.last_limit == 50


def test_candles_limit_capped_at_500(env):
    client, _store, feed, _cfg = env
    client.get("/api/candles?limit=9999")
    assert feed.last_limit == 500


def test_candles_cached_within_ttl(env):
    client, _store, feed, _cfg = env
    client.get("/api/candles?symbol=BTC/USDT&timeframe=1h&limit=50")
    client.get("/api/candles?symbol=BTC/USDT&timeframe=1h&limit=50")
    assert feed.calls == 1  # la segunda salió del cache


def test_candles_error_returns_empty_list(env):
    client, _store, _feed, _cfg = env
    app.dependency_overrides[get_candle_feed] = lambda: BoomFeed()
    r = client.get("/api/candles")
    assert r.status_code == 200
    assert r.json() == []


def test_get_candle_feed_returns_set_singleton():
    fake = FakeFeed()
    set_candle_feed(fake)
    try:
        # con el singleton seteado no se construye ningún exchange (no red)
        assert get_candle_feed(Config()) is fake
    finally:
        set_candle_feed(None)
