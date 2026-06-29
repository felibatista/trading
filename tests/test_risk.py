from bot.config import RiskParams
from bot.risk.manager import can_open, size_quantity, stop_loss_price, take_profit_price


def test_size_quantity_capped_by_max_exposure():
    p = RiskParams(risk_per_trade=0.01, stop_loss_pct=0.02, max_exposure_pct=0.30)
    # riesgo: 100 / (100*0.02)=50 -> notional 5000 > 3000 -> topea a 30
    assert abs(size_quantity(10000.0, 100.0, p) - 30.0) < 1e-9


def test_size_quantity_not_capped():
    p = RiskParams(risk_per_trade=0.01, stop_loss_pct=0.10, max_exposure_pct=0.30)
    # 100 / (100*0.10)=10 -> notional 1000 < 3000 -> 10
    assert abs(size_quantity(10000.0, 100.0, p) - 10.0) < 1e-9


def test_stop_and_take_prices():
    p = RiskParams(stop_loss_pct=0.02, take_profit_pct=0.04)
    assert abs(stop_loss_price(100.0, p) - 98.0) < 1e-9
    assert abs(take_profit_price(100.0, p) - 104.0) < 1e-9


def test_can_open_respects_max_positions():
    p = RiskParams(max_positions=3)
    assert can_open(2, p) is True
    assert can_open(3, p) is False
