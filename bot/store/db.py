# bot/store/db.py
from __future__ import annotations

from sqlalchemy import delete, insert, select, update

from bot.broker.models import Fill, Position
from bot.store.engine import make_engine
from bot.store.schema import accounts, decisions, equity, fills, metadata, positions


class Store:
    def __init__(self, target: str = ":memory:") -> None:
        self._engine = make_engine(target)
        metadata.create_all(self._engine)

    # ---- decisiones ----
    def record_decision(
        self, account: str, ts: str, symbol: str, action: str, reason: str,
        ema_fast: float, ema_slow: float, rsi: float,
        ai_action: str | None = None,
        ai_confidence: float | None = None,
        ai_rationale: str | None = None,
    ) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(decisions).values(
                account=account, ts=ts, symbol=symbol, action=action, reason=reason,
                ema_fast=ema_fast, ema_slow=ema_slow, rsi=rsi,
                ai_action=ai_action, ai_confidence=ai_confidence, ai_rationale=ai_rationale,
            ))

    def recent_decisions(self, account: str, limit: int = 10) -> list[dict]:
        cols = [
            decisions.c.ts, decisions.c.symbol, decisions.c.action, decisions.c.reason,
            decisions.c.ema_fast, decisions.c.ema_slow, decisions.c.rsi,
            decisions.c.ai_action, decisions.c.ai_confidence, decisions.c.ai_rationale,
        ]
        stmt = (
            select(*cols)
            .where(decisions.c.account == account)
            .order_by(decisions.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    # ---- equity ----
    def record_equity(self, account: str, ts: str, equity_value: float, cash: float) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(equity).values(
                account=account, ts=ts, equity=equity_value, cash=cash,
            ))

    def latest_equity(self, account: str) -> tuple[float, float] | None:
        stmt = (
            select(equity.c.equity, equity.c.cash)
            .where(equity.c.account == account)
            .order_by(equity.c.id.desc())
            .limit(1)
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        return None if row is None else (row.equity, row.cash)

    def equity_series(self, account: str, limit: int = 200) -> list[dict]:
        stmt = (
            select(equity.c.ts, equity.c.equity, equity.c.cash)
            .where(equity.c.account == account)
            .order_by(equity.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(stmt)]
        return list(reversed(rows))

    def close(self) -> None:
        self._engine.dispose()
