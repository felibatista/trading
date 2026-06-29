# tests/test_api_accounts.py
from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app
from api.deps import get_store
from bot.store.db import Store


def _client_with_store(store):
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_accounts_listed_with_equity():
    store = Store(":memory:")
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2})
    store.record_equity("scalper", "2026-01-01T00:00:00+00:00", 10100.0, 9000.0)
    client = _client_with_store(store)
    r = client.get("/api/accounts")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["id"] == "scalper" and body[0]["equity"] == 10100.0


def test_status_scoped_by_account_query():
    store = Store(":memory:")
    store.record_equity("default", "2026-01-01T00:00:00+00:00", 10000.0, 10000.0)
    store.record_equity("other", "2026-01-01T00:00:00+00:00", 5000.0, 5000.0)
    client = _client_with_store(store)
    assert client.get("/api/status").json()["equity"] == 10000.0          # default
    assert client.get("/api/status?account=other").json()["equity"] == 5000.0


def test_accounts_include_starting_cash():
    from bot.store.db import Store
    store = Store(":memory:")
    store.upsert_account("scalper", "Scalper", "ema_rsi", "BTC/USDT", "1m", 12,
                         10000.0, True, True, {"fast": 2})
    store.record_equity("scalper", "2026-01-01T00:00:00+00:00", 10500.0, 9000.0)
    client = _client_with_store(store)
    body = client.get("/api/accounts").json()
    assert body[0]["starting_cash"] == 10000.0
    assert body[0]["equity"] == 10500.0
