from __future__ import annotations

from bot.backtest.report import format_table, iso_to_ms, resolve_window
from bot.backtest.runner import BacktestResult


def test_resolve_window_days():
    now = 10_000_000_000
    since, until = resolve_window(now, days=7)
    assert until == now
    assert since == now - 7 * 86_400_000


def test_resolve_window_from_to_overrides_days():
    now = 10_000_000_000
    since, until = resolve_window(now, days=7, from_="2026-06-01", to="2026-06-08")
    assert since == iso_to_ms("2026-06-01")
    assert until == iso_to_ms("2026-06-08")
    assert until - since == 7 * 86_400_000


def test_format_table_sorts_by_return_and_marks_ai():
    results = [
        BacktestResult("a", "A", "ema_rsi", False, 5.0, 2.0, 0.5, 3, 10500.0, 0.3, 10000.0),
        BacktestResult("p", "P", "price_action", True, 12.0, 1.0, 0.6, 4, 11200.0, 0.4, 10000.0),
    ]
    out = format_table(results, "7d")
    lines = out.splitlines()
    assert "price_action" in lines[2]  # mayor retorno primero
    assert "ema_rsi" in lines[3]
    assert out.count("sí") == 1        # solo price_action marca IA
