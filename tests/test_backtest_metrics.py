from __future__ import annotations

from bot.backtest.metrics import (
    ClosedTrade,
    closed_trades,
    max_drawdown_pct,
    profit_factor,
    sharpe_ratio,
    total_return_pct,
    win_rate,
)


def _curve(*equities: float) -> list[dict]:
    return [{"ts": str(i), "equity": e, "cash": e} for i, e in enumerate(equities)]


def test_total_return_pct():
    assert round(total_return_pct(_curve(10000, 11000), 10000), 6) == 10.0
    assert round(total_return_pct(_curve(10000, 9000), 10000), 6) == -10.0
    assert total_return_pct([], 10000) == 0.0
    assert total_return_pct(_curve(10000), 0) == 0.0


def test_max_drawdown_pct():
    # sube a 120, cae a 90 (peak 120 -> 90 = -25%), recupera
    assert round(max_drawdown_pct(_curve(100, 120, 90, 110)), 2) == 25.0
    # monótona creciente -> sin drawdown
    assert max_drawdown_pct(_curve(100, 110, 120)) == 0.0
    assert max_drawdown_pct([]) == 0.0


def test_closed_trades_pairs_buy_then_sell_with_fees():
    fills = [
        {"side": "BUY", "quantity": 1.0, "price": 100.0, "fee": 1.0},
        {"side": "SELL", "quantity": 1.0, "price": 110.0, "fee": 1.1},
        {"side": "BUY", "quantity": 2.0, "price": 50.0, "fee": 1.0},
        {"side": "SELL", "quantity": 2.0, "price": 40.0, "fee": 0.8},
    ]
    trades = closed_trades(fills)
    assert len(trades) == 2
    # trade 1: proceeds 110-1.1=108.9, cost 100+1=101 -> +7.9
    assert round(trades[0].pnl, 2) == 7.9
    # trade 2: proceeds 80-0.8=79.2, cost 100+1=101 -> -21.8
    assert round(trades[1].pnl, 2) == -21.8


def test_closed_trades_ignores_unclosed_buy():
    fills = [{"side": "BUY", "quantity": 1.0, "price": 100.0, "fee": 1.0}]
    assert closed_trades(fills) == []


def test_win_rate():
    trades = [
        ClosedTrade(1, 100, 110, 7.9),
        ClosedTrade(1, 100, 90, -11.0),
        ClosedTrade(1, 100, 105, 4.0),
    ]
    assert round(win_rate(trades), 4) == round(2 / 3, 4)
    assert win_rate([]) == 0.0


def test_profit_factor():
    trades = [ClosedTrade(1, 100, 110, 10.0), ClosedTrade(1, 100, 95, -5.0),
              ClosedTrade(1, 100, 90, -5.0)]
    assert profit_factor(trades) == 1.0          # 10 / (5+5)
    assert profit_factor([]) is None              # sin trades
    assert profit_factor([ClosedTrade(1, 100, 110, 8.0)]) is None  # sin pérdidas → ∞


def test_sharpe_ratio():
    assert sharpe_ratio([], 252) == 0.0
    assert sharpe_ratio(_curve(100), 252) == 0.0  # un punto, sin retornos
    # equity que sube de forma constante (retorno por período constante) → desvío 0 → 0.0
    assert sharpe_ratio(_curve(100, 110, 121), 252) == 0.0
    # con varianza, Sharpe positivo y escala con sqrt(periods_per_year)
    up = sharpe_ratio(_curve(100, 101, 100.5, 102, 101.5, 103), 252)
    assert up > 0
    assert sharpe_ratio(_curve(100, 90, 95, 85, 80), 252) < 0  # tendencia bajista
