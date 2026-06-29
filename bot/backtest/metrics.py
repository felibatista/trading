from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClosedTrade:
    """Un round-trip COMPRA→VENTA ya cerrado. `pnl` es neto (incluye fees y slippage,
    que ya vienen embebidos en el precio/fee de cada fill)."""

    quantity: float
    entry_price: float
    exit_price: float
    pnl: float


def total_return_pct(curve: list[dict], starting_cash: float) -> float:
    """Retorno % sobre el capital inicial, a partir de la curva de equity."""
    if not curve or starting_cash <= 0:
        return 0.0
    return (curve[-1]["equity"] / starting_cash - 1.0) * 100.0


def max_drawdown_pct(curve: list[dict]) -> float:
    """Peor caída pico-a-valle de la equity, como magnitud NO negativa (0.0 = sin caída)."""
    peak = float("-inf")
    worst = 0.0
    for point in curve:
        equity = point["equity"]
        if equity > peak:
            peak = equity
        if peak > 0:
            drop = (equity / peak - 1.0) * 100.0  # <= 0
            if drop < worst:
                worst = drop
    return abs(worst)


def closed_trades(fills: list[dict]) -> list[ClosedTrade]:
    """Empareja BUY→SELL en orden. Cada cuenta opera un único símbolo y mantiene a lo
    sumo una posición por símbolo (el motor solo compra si no hay posición), así que el
    emparejamiento es secuencial: una compra abierta a la vez."""
    trades: list[ClosedTrade] = []
    open_buy: dict | None = None
    for f in fills:
        if f["side"] == "BUY":
            open_buy = f
        elif f["side"] == "SELL" and open_buy is not None:
            cost = open_buy["quantity"] * open_buy["price"] + open_buy["fee"]
            proceeds = f["quantity"] * f["price"] - f["fee"]
            trades.append(ClosedTrade(
                quantity=f["quantity"],
                entry_price=open_buy["price"],
                exit_price=f["price"],
                pnl=proceeds - cost,
            ))
            open_buy = None
    return trades


def win_rate(trades: list[ClosedTrade]) -> float:
    """Fracción de trades cerrados con PnL positivo (0.0 si no hay trades cerrados)."""
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.pnl > 0)
    return wins / len(trades)


def returns_from_curve(curve: list[dict]) -> list[float]:
    """Retornos simples punto a punto de la curva de equity."""
    rets: list[float] = []
    for i in range(1, len(curve)):
        prev = curve[i - 1]["equity"]
        if prev > 0:
            rets.append(curve[i]["equity"] / prev - 1.0)
    return rets


def sharpe_ratio(curve: list[dict], periods_per_year: float) -> float:
    """Sharpe ANUALIZADO (risk-free 0) sobre los retornos por período de la equity.
    Anualizar es lo que hace comparables estrategias en timeframes distintos.
    0.0 si no hay suficientes datos o el desvío es nulo."""
    rets = returns_from_curve(curve)
    n = len(rets)
    if n < 2:
        return 0.0
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)  # desvío muestral
    if var <= 0:
        return 0.0
    return (mean / var ** 0.5) * (periods_per_year ** 0.5)


def profit_factor(trades: list[ClosedTrade]) -> float | None:
    """Ganancia bruta / pérdida bruta de los trades cerrados. None = sin pérdidas
    (PF indefinido / ∞) o sin trades; el caller lo distingue por num_trades."""
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = -sum(t.pnl for t in trades if t.pnl < 0)
    if gross_loss <= 0:
        return None
    return gross_win / gross_loss
