from __future__ import annotations

import pandas as pd

from bot.backtest.runner import BacktestResult


def iso_to_ms(value: str) -> int:
    """ISO/fecha → epoch ms en UTC. Acepta 'YYYY-MM-DD' o ISO con/sin zona."""
    ts = pd.Timestamp(value)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return int(ts.timestamp() * 1000)


def resolve_window(
    now_ms: int, *, days: int = 7, from_: str | None = None, to: str | None = None
) -> tuple[int, int]:
    """Devuelve (since_ms, until_ms). `now_ms` se inyecta (testable). `from/to` pisan días."""
    until = iso_to_ms(to) if to else now_ms
    since = iso_to_ms(from_) if from_ else until - days * 86_400_000
    return since, until


def format_table(results: list[BacktestResult], label: str) -> str:
    rows = sorted(results, key=lambda r: r.return_pct, reverse=True)
    lines = [
        f"Backtest {label} · {len(results)} estrategias",
        f"{'estrategia':<14}{'ret%':>9}{'maxDD%':>9}{'win%':>8}{'#tr':>6}{'equity':>12}  IA",
    ]
    for r in rows:
        lines.append(
            f"{r.strategy:<14}{r.return_pct:>9.2f}{r.max_drawdown_pct:>9.2f}"
            f"{r.win_rate * 100:>8.1f}{r.num_trades:>6}{r.final_equity:>12.2f}"
            f"  {'sí' if r.ai else 'no'}"
        )
    return "\n".join(lines)
