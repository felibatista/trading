from __future__ import annotations

import math
import time

from fastapi.testclient import TestClient

import api.app as appmod
from api.app import create_app, get_backtest_advisor_factory, get_backtest_exchange
from bot.backtest.data import timeframe_to_ms
from bot.models import AIVerdict


class FakeExchange:
    """Genera OHLCV sintético continuo (oscila) para cualquier `since`, sin red."""

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        tf = timeframe_to_ms(timeframe)
        base = since // tf
        return [
            [since + i * tf, 100.0, 101.0, 99.0, 100.0 + 5.0 * math.sin((base + i) / 2.0), 1.0]
            for i in range(limit)
        ]


class _StubAdvisor:
    enabled = True

    def review(self, ctx) -> AIVerdict:
        return AIVerdict(confirm=True, confidence=1.0, rationale="stub", ai_used=True)


def _stub_factory(provider, model, timeout, retries):
    return _StubAdvisor()


def _client() -> TestClient:
    # Estado de backtest es a nivel módulo: limpiar entre tests para aislarlos.
    appmod._backtest_cache.clear()
    appmod._backtest_jobs.clear()
    if appmod._backtest_lock.locked():
        appmod._backtest_lock.release()
    app = create_app()
    app.dependency_overrides[get_backtest_exchange] = lambda: FakeExchange()
    app.dependency_overrides[get_backtest_advisor_factory] = lambda: _stub_factory
    return TestClient(app)


def _run(client: TestClient, payload: dict, timeout_s: float = 15.0) -> list[dict]:
    r = client.post("/api/backtest", json=payload)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        s = client.get(f"/api/backtest/{job_id}").json()
        if s["status"] == "done":
            return s["results"]
        if s["status"] == "error":
            raise AssertionError(f"job error: {s['error']}")
        time.sleep(0.1)
    raise AssertionError("el job no terminó a tiempo")


def test_backtest_job_returns_five_results_ai_only_price_action():
    body = _run(_client(), {"days": 1})
    assert len(body) == 5
    by_strat = {x["strategy"]: x for x in body}
    assert by_strat["price_action"]["ai"] is True
    assert all(x["ai"] is False for x in body if x["strategy"] != "price_action")
    for x in body:
        assert isinstance(x["equity_curve"], list)
        assert len(x["equity_curve"]) <= 300
        assert {"return_pct", "max_drawdown_pct", "win_rate", "num_trades", "starting_cash"} <= set(x)
    assert len(by_strat["price_action"]["equity_curve"]) > 0


def test_backtest_accepts_from_to_alias():
    body = _run(_client(), {"from": "2026-06-01", "to": "2026-06-02"})
    assert len(body) == 5


def test_backtest_unknown_job_404():
    assert _client().get("/api/backtest/noexiste").status_code == 404


def test_backtest_rejects_invalid_date():
    r = _client().post("/api/backtest", json={"from": "ayer", "to": "2026-06-02"})
    assert r.status_code == 422  # validado en el modelo, no 500 crudo


def test_backtest_rejects_oversized_window():
    r = _client().post("/api/backtest", json={"from": "2020-01-01", "to": "2026-06-02"})
    assert r.status_code == 422  # ventana > ~31 días


def test_backtest_rejects_inverted_window():
    r = _client().post("/api/backtest", json={"from": "2026-06-10", "to": "2026-06-01"})
    assert r.status_code == 422
