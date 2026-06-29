from __future__ import annotations

import math

import pandas as pd

from bot.accounts import DEFAULT_ACCOUNTS
from bot.backtest.runner import run_backtest, run_fleet_backtest
from bot.config import RiskParams
from bot.models import AIVerdict


def _osc_df(n: int) -> pd.DataFrame:
    # Sierra que oscila ~92..108 (amplitud 8%): cruza EMAs y dispara SL/TP repetidamente.
    closes = [100.0 + 8.0 * math.sin(i / 2.0) for i in range(n)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(range(n), unit="m", utc=True),
        "open": closes, "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes], "close": closes, "volume": [1.0] * n,
    })


_SCALPER = {
    "id": "scalper", "name": "Scalper", "strategy": "ema_rsi", "symbol": "BTC/USDT",
    "timeframe": "1m", "interval_seconds": 12, "starting_cash": 10000.0,
    "params": {"fast": 2, "slow": 4, "rsi_period": 7, "rsi_oversold": 20.0, "rsi_overbought": 85.0},
}


class StubAdvisor:
    enabled = True

    def __init__(self, confirm: bool) -> None:
        self._confirm = confirm
        self.calls = 0

    def review(self, ctx) -> AIVerdict:
        self.calls += 1
        return AIVerdict(confirm=self._confirm, confidence=1.0, rationale="stub", ai_used=True)


def _reconciles(res) -> bool:
    # Invariante: la suma del PnL de los trades == ganancia de la equity (incluida la
    # posición abierta al final, que se cierra sintéticamente al precio de marca).
    pnl = sum(t.pnl for t in res.trades)
    return abs(pnl - (res.final_equity - res.starting_cash)) < 1e-6


def test_run_backtest_without_ai_trades():
    res = run_backtest(_SCALPER, _osc_df(120), risk=RiskParams(), warmup=10, limit=50)
    assert res.ai is False
    assert res.num_trades >= 1            # la sierra dispara entradas + salidas por SL/TP
    assert res.exposure > 0.0
    assert len(res.equity_curve) > 0
    assert res.starting_cash == 10000.0
    assert _reconciles(res)               # métricas de trades coherentes con la equity


def test_metrics_reconcile_with_open_position():
    # Serie que baja y repunta al final: abre una compra cerca del cierre y termina EN
    # posición. El cierre sintético hace que sum(pnl) == final_equity - starting_cash.
    closes = [100.0 - i * 0.5 for i in range(36)] + [82.5, 83.6, 84.8, 86.0]
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(range(len(closes)), unit="m", utc=True),
        "open": closes, "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes], "close": closes, "volume": [1.0] * len(closes),
    })
    res = run_backtest(_SCALPER, df, risk=RiskParams(), warmup=10, limit=50)
    assert _reconciles(res)


def test_ai_veto_blocks_all_entries():
    veto = StubAdvisor(confirm=False)
    res = run_backtest(_SCALPER, _osc_df(120), risk=RiskParams(), advisor=veto, warmup=10, limit=50)
    assert res.ai is True
    assert veto.calls >= 1                 # se consultó a la IA en las entradas
    assert res.num_trades == 0             # vetó todas: nunca abrió posición
    assert res.exposure == 0.0
    assert res.final_equity == 10000.0     # equity intacta: no operó


def test_ai_confirm_allows_trades():
    ok = StubAdvisor(confirm=True)
    res = run_backtest(_SCALPER, _osc_df(120), risk=RiskParams(), advisor=ok, warmup=10, limit=50)
    assert res.ai is True and ok.calls >= 1
    assert res.num_trades >= 1             # confirmó: opera como sin IA
    assert _reconciles(res)


def test_fleet_applies_ai_only_to_price_action():
    candles_by_tf = {tf: _osc_df(260) for tf in ("1m", "5m", "15m", "30m", "1h")}
    factory_calls = []

    def factory(provider, model, timeout, retries):
        factory_calls.append((provider, model))
        return StubAdvisor(confirm=True)

    results = run_fleet_backtest(
        DEFAULT_ACCOUNTS, candles_by_tf, risk=RiskParams(), advisor_factory=factory,
    )
    assert len(results) == 5
    by_strat = {r.strategy: r for r in results}
    assert by_strat["price_action"].ai is True
    assert all(r.ai is False for r in results if r.strategy != "price_action")
    # el advisor se construyó UNA sola vez, para price_action, con openai/gpt-4o-mini
    assert factory_calls == [("openai", "gpt-4o-mini")]
