from __future__ import annotations

from bot.broker.models import Fill, Side


class LocalPaperBroker:
    def __init__(self, cash: float, fee_rate: float = 0.001, slippage: float = 0.0005) -> None:
        self._cash = float(cash)
        self.fee_rate = fee_rate
        self.slippage = slippage
        self._holdings: dict[str, float] = {}

    def cash(self) -> float:
        return self._cash

    def holdings(self, symbol: str) -> float:
        return self._holdings.get(symbol, 0.0)

    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        fill_price = ref_price * (1 + self.slippage)
        cost = quantity * fill_price
        fee = cost * self.fee_rate
        total = cost + fee
        if total > self._cash + 1e-9:
            raise ValueError(
                f"Saldo insuficiente: necesita {total:.2f}, tiene {self._cash:.2f}"
            )
        self._cash -= total
        self._holdings[symbol] = self._holdings.get(symbol, 0.0) + quantity
        return Fill(symbol, Side.BUY, quantity, fill_price, fee)

    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        held = self._holdings.get(symbol, 0.0)
        if quantity > held + 1e-9:
            raise ValueError(
                f"Posición insuficiente en {symbol}: vende {quantity}, tiene {held}"
            )
        fill_price = ref_price * (1 - self.slippage)
        proceeds = quantity * fill_price
        fee = proceeds * self.fee_rate
        self._cash += proceeds - fee
        self._holdings[symbol] = held - quantity
        return Fill(symbol, Side.SELL, quantity, fill_price, fee)
