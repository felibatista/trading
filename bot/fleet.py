# bot/fleet.py
from __future__ import annotations

import json
import threading
from typing import Callable

from bot.broker.paper import LocalPaperBroker
from bot.cli import make_advisor
from bot.config import Config
from bot.data.feed import CcxtDataFeed, DataFeed
from bot.engine.runner import Engine
from bot.store.db import Store
from bot.strategy.registry import get_strategy


class Fleet:
    def __init__(
        self,
        store: Store,
        config: Config,
        feed_factory: Callable[[], DataFeed] | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self.store = store
        self.config = config
        self.feed_factory = feed_factory or (lambda: CcxtDataFeed(config.exchange))
        self.log = log
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    def _build_broker(self, account: dict) -> LocalPaperBroker:
        bp = self.config.broker
        eq = self.store.latest_equity(account["id"])
        cash = eq[1] if eq is not None else account["starting_cash"]
        positions = self.store.get_positions(account["id"])
        holdings = {s: p.quantity for s, p in positions.items()} or None
        return LocalPaperBroker(cash, bp.fee_rate, bp.slippage, holdings=holdings)

    def _build_engine(self, account: dict) -> Engine:
        ai_on = bool(account["ai_enabled"])
        # IA por cuenta: la enciende el flag de la cuenta + el master global (cfg.ai.enabled),
        # y cada cuenta elige su proveedor/modelo. timeout/retries siguen globales.
        cfg = self.config
        advisor = (
            make_advisor(
                account["ai_provider"], account["ai_model"],
                cfg.ai.timeout_seconds, cfg.ai.max_retries,
            )
            if (ai_on and cfg.ai.enabled)
            else None
        )
        return Engine(
            feed=self.feed_factory(),
            broker=self._build_broker(account),
            store=self.store,
            strategy=account["params"],
            risk=cfg.risk,
            timeframe=account["timeframe"],
            limit=cfg.limit,
            decider=get_strategy(account["strategy"]),
            advisor=advisor,
            ai_affects_execution=(ai_on and cfg.ai.enabled and cfg.broker.kind == "paper"),
            account=account["id"],
        )

    @staticmethod
    def _config_sig(account: dict) -> tuple:
        return (
            account["strategy"],
            json.dumps(account.get("params") or {}, sort_keys=True),
            account["symbol"],
            account["timeframe"],
            bool(account["ai_enabled"]),
            account.get("ai_provider"),
            account.get("ai_model"),
        )

    def run_once(self) -> None:
        for account in self.store.list_accounts():
            if not account["enabled"]:
                continue
            try:
                engine = self._build_engine(account)
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001 - aislar fallos por cuenta
                self.log(f"[{account['id']}] ERROR: {exc}")

    def _loop(self, account_id: str) -> None:
        engine = None
        sig = None
        while not self._stop.is_set():
            account = self.store.get_account(account_id)
            if account is None:
                return
            interval = account["interval_seconds"]
            if not account["enabled"]:
                self._stop.wait(interval)
                continue
            new_sig = self._config_sig(account)
            if engine is None or new_sig != sig:
                try:
                    engine = self._build_engine(account)
                    sig = new_sig
                    self.log(f"[{account_id}] config (re)cargada")
                except Exception as exc:  # noqa: BLE001
                    self.log(f"[{account_id}] ERROR al construir engine: {exc}")
                    self._stop.wait(interval)
                    continue
            try:
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001
                self.log(f"[{account_id}] ERROR: {exc}")
            self._stop.wait(interval)

    def start(self) -> None:
        self._stop.clear()
        self._threads.clear()
        for account in self.store.list_accounts():
            t = threading.Thread(
                target=self._loop, args=(account["id"],),
                name=f"fleet-{account['id']}", daemon=True,
            )
            t.start()
            self._threads.append(t)
        self.log(f"Flota arriba: {len(self._threads)} cuentas")

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout)
        self._threads.clear()
