from __future__ import annotations

import math

from fastapi.testclient import TestClient

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
    app = create_app()
    app.dependency_overrides[get_backtest_exchange] = lambda: FakeExchange()
    app.dependency_overrides[get_backtest_advisor_factory] = lambda: _stub_factory
    return TestClient(app)


def test_backtest_endpoint_returns_five_results_ai_only_price_action():
    r = _client().post("/api/backtest", json={"days": 1})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 5
    by_strat = {x["strategy"]: x for x in body}
    assert by_strat["price_action"]["ai"] is True
    assert all(x["ai"] is False for x in body if x["strategy"] != "price_action")
    for x in body:
        assert isinstance(x["equity_curve"], list)
        assert len(x["equity_curve"]) <= 300        # downsampleado
        assert {"return_pct", "max_drawdown_pct", "win_rate", "num_trades"} <= set(x)
    assert len(by_strat["price_action"]["equity_curve"]) > 0  # corrió de verdad


def test_backtest_accepts_from_to_alias():
    r = _client().post("/api/backtest", json={"from": "2026-06-01", "to": "2026-06-02"})
    assert r.status_code == 200
    assert len(r.json()) == 5
