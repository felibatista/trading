from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Fill:
    symbol: str
    side: Side
    quantity: float
    price: float
    fee: float


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
