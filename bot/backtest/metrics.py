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
