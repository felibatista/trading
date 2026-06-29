# tests/test_api_account_update.py
from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_store
from bot.store.db import Store


def _client(store):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def _seed(store):
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2, "slow": 4})


def test_put_updates_editable_fields():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    r = client.put("/api/accounts/scalper", json={
        "timeframe": "5m", "interval_seconds": 30, "ai_enabled": False,
        "enabled": False, "params": {"fast": 3, "slow": 9},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["timeframe"] == "5m" and body["ai_enabled"] is False and body["enabled"] is False
    acc = store.get_account("scalper")
    assert acc["params"] == {"fast": 3, "slow": 9} and acc["interval_seconds"] == 30


def test_put_updates_ai_provider_and_model():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    r = client.put("/api/accounts/scalper", json={
        "ai_provider": "openai", "ai_model": "gpt-4o-mini",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ai_provider"] == "openai" and body["ai_model"] == "gpt-4o-mini"
    acc = store.get_account("scalper")
    assert acc["ai_provider"] == "openai" and acc["ai_model"] == "gpt-4o-mini"


def test_put_rejects_bad_provider():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    assert client.put("/api/accounts/scalper", json={"ai_provider": "gemini"}).status_code == 422


def test_put_unknown_account_404():
    store = Store(":memory:")
    client = _client(store)
    assert client.put("/api/accounts/noexiste", json={"enabled": False}).status_code == 404


def test_put_rejects_bad_strategy():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    assert client.put("/api/accounts/scalper", json={"strategy": "inventada"}).status_code == 422


def test_put_rejects_bad_interval():
    store = Store(":memory:")
    _seed(store)
    client = _client(store)
    assert client.put("/api/accounts/scalper", json={"interval_seconds": 1}).status_code == 422
