from __future__ import annotations

from typing import Protocol

from bot.broker.models import Fill


class Broker(Protocol):
    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill: ...
    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill: ...
    def cash(self) -> float: ...
