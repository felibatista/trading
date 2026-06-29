# bot/fleet.py
from __future__ import annotations

import threading
from typing import Callable

from bot.broker.paper import LocalPaperBroker
from bot.cli import ai_affects_execution, build_advisor
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
        self._pairs: list[tuple[dict, Engine]] = []
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
        # build_advisor mira config.ai.enabled; lo respetamos por cuenta clonando el flag.
        cfg = self.config
        advisor = build_advisor(cfg) if (ai_on and cfg.ai.enabled) else None
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
            ai_affects_execution=(ai_on and cfg.broker.kind == "paper"),
            account=account["id"],
        )

    def _setup(self) -> None:
        if self._pairs:
            return
        self._pairs = [
            (a, self._build_engine(a))
            for a in self.store.list_accounts()
            if a["enabled"]
        ]

    def run_once(self) -> None:
        self._setup()
        for account, engine in self._pairs:
            try:
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001 - aislar fallos por cuenta
                self.log(f"[{account['id']}] ERROR: {exc}")

    def _loop(self, account: dict, engine: Engine) -> None:
        while not self._stop.is_set():
            try:
                engine.run_cycle(account["symbol"])
            except Exception as exc:  # noqa: BLE001
                self.log(f"[{account['id']}] ERROR: {exc}")
            self._stop.wait(account["interval_seconds"])

    def start(self) -> None:
        self._setup()
        self._stop.clear()
        for account, engine in self._pairs:
            t = threading.Thread(
                target=self._loop, args=(account, engine),
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
