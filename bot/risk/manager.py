from __future__ import annotations

from bot.config import RiskParams


def size_quantity(equity: float, price: float, params: RiskParams) -> float:
    per_unit_risk = price * params.stop_loss_pct
    if per_unit_risk <= 0:
        return 0.0
    risk_amount = equity * params.risk_per_trade
    quantity = risk_amount / per_unit_risk
    max_notional = equity * params.max_exposure_pct
    if quantity * price > max_notional:
        quantity = max_notional / price
    return quantity


def stop_loss_price(entry: float, params: RiskParams) -> float:
    return entry * (1 - params.stop_loss_pct)


def take_profit_price(entry: float, params: RiskParams) -> float:
    return entry * (1 + params.take_profit_pct)


def can_open(open_positions: int, params: RiskParams) -> bool:
    return open_positions < params.max_positions
