from __future__ import annotations

from typing import Any

from bot.broker.models import Fill, Side


class OkxDemoBroker:
    def __init__(
        self,
        api_key: str,
        secret: str,
        password: str,
        quote: str = "USDT",
        exchange: Any | None = None,
    ) -> None:
        self.quote = quote
        if exchange is None:
            import ccxt

            exchange = ccxt.okx(
                {
                    "apiKey": api_key,
                    "secret": secret,
                    "password": password,
                    "enableRateLimit": True,
                }
            )
            exchange.set_sandbox_mode(True)
        self._exchange = exchange

    def cash(self) -> float:
        balance = self._exchange.fetch_balance()
        return float(balance["free"].get(self.quote, 0.0))

    def buy(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        order = self._exchange.create_market_buy_order(symbol, quantity)
        return self._to_fill(order, symbol, Side.BUY)

    def sell(self, symbol: str, quantity: float, ref_price: float) -> Fill:
        order = self._exchange.create_market_sell_order(symbol, quantity)
        return self._to_fill(order, symbol, Side.SELL)

    @staticmethod
    def _to_fill(order: dict, symbol: str, side: Side) -> Fill:
        price = float(order.get("average") or order.get("price") or 0.0)
        quantity = float(order.get("filled") or order.get("amount") or 0.0)
        fee_info = order.get("fee") or {}
        fee = float(fee_info.get("cost") or 0.0)
        return Fill(symbol, side, quantity, price, fee)
