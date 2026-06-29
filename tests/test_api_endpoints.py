import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.deps import get_config, get_store
from bot.broker.models import Fill, Position, Side
from bot.config import BrokerParams, Config
from bot.store.db import Store


@pytest.fixture
def client():
    store = Store(":memory:")
    store.record_equity("default", "2024-01-01T00:00:00+00:00", 10000.0, 10000.0)
    store.record_equity("default", "2024-01-01T01:00:00+00:00", 10120.0, 9000.0)
    store.record_fill("default", "2024-01-01T01:00:00+00:00", Fill("BTC/USDT", Side.BUY, 0.01, 100.0, 0.001))
    store.upsert_position(
        "default", Position("BTC/USDT", 0.01, 100.0, 98.0, 104.0), "2024-01-01T01:00:00+00:00"
    )
    store.record_decision(
        "default", "2024-01-01T01:00:00+00:00", "BTC/USDT", "BUY", "cruce alcista", 30.5, 29.0, 41.0
    )

    cfg = Config(
        exchange="okx", timeframe="1h", symbols=["BTC/USDT"],
        broker=BrokerParams(kind="paper"),
    )

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_config] = lambda: cfg
    yield TestClient(app)
    app.dependency_overrides.clear()
    store.close()


def test_status_endpoint(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["exchange"] == "okx"
    assert body["timeframe"] == "1h"
    assert body["broker_kind"] == "paper"
    assert body["symbols"] == ["BTC/USDT"]
    assert body["equity"] == 10120.0
    assert body["cash"] == 9000.0


def test_equity_endpoint_chronological(client):
    r = client.get("/api/equity?limit=10")
    assert r.status_code == 200
    series = r.json()
    assert [p["equity"] for p in series] == [10000.0, 10120.0]
    assert set(series[0]) == {"ts", "equity", "cash"}


def test_positions_endpoint(client):
    r = client.get("/api/positions")
    assert r.status_code == 200
    pos = r.json()
    assert len(pos) == 1
    assert pos[0]["symbol"] == "BTC/USDT"
    assert pos[0]["entry_price"] == 100.0
    assert pos[0]["stop_loss"] == 98.0


def test_decisions_endpoint_with_indicators(client):
    r = client.get("/api/decisions?limit=5")
    assert r.status_code == 200
    decisions = r.json()
    assert len(decisions) == 1
    d = decisions[0]
    assert d["action"] == "BUY"
    assert d["reason"] == "cruce alcista"
    assert d["rsi"] == 41.0
    assert d["ema_fast"] == 30.5
    assert d["ema_slow"] == 29.0


def test_fills_endpoint(client):
    r = client.get("/api/fills?limit=10")
    assert r.status_code == 200
    fills = r.json()
    assert len(fills) == 1
    assert fills[0]["side"] == "BUY"
    assert fills[0]["price"] == 100.0
    assert fills[0]["quantity"] == 0.01


def test_cors_allows_dev_origin(client):
    r = client.get("/api/status", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
