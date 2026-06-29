# bot/store/db.py
from __future__ import annotations

from sqlalchemy import delete, insert, inspect, select, text, update

from bot.broker.models import Fill, Position
from bot.store.engine import make_engine
from bot.store.schema import accounts, decisions, equity, fills, metadata, positions


class Store:
    def __init__(self, target: str = ":memory:", *, use_env_url: bool = True) -> None:
        # use_env_url=False fuerza la DB de `target` (p. ej. :memory:) ignorando
        # DATABASE_URL: clave para que el backtest NO escriba en producción.
        self._engine = make_engine(target, use_env_url=use_env_url)
        metadata.create_all(self._engine)
        self._migrate_legacy()
        self._migrate_accounts()

    def _migrate_legacy(self) -> None:
        # Solo SQLite: adapta tablas creadas con esquemas viejos.
        if self._engine.dialect.name != "sqlite":
            return
        insp = inspect(self._engine)
        existing = set(insp.get_table_names())
        # Agrega columna account (ADD COLUMN conserva el resto de las filas).
        for table in ("decisions", "fills", "equity"):
            if table not in existing:
                continue
            cols = {c["name"] for c in insp.get_columns(table)}
            if "account" not in cols:
                with self._engine.begin() as conn:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN account TEXT NOT NULL DEFAULT 'default'"
                    ))
        # positions necesita PK compuesta (account, symbol). Un ADD COLUMN no cambia
        # la PK vieja (solo `symbol`), así que si la PK no es la compuesta reconstruimos
        # la tabla. Detectamos por PK (no por columna) para reparar también una DB ya
        # migrada por la versión anterior (que dejó account pero la PG vieja).
        if "positions" in existing:
            pk = set(insp.get_pk_constraint("positions").get("constrained_columns") or [])
            if pk != {"account", "symbol"}:
                legacy_cols = {c["name"] for c in insp.get_columns("positions")}
                acct = "account" if "account" in legacy_cols else "'default'"
                with self._engine.begin() as conn:
                    conn.execute(text("ALTER TABLE positions RENAME TO positions_legacy"))
                positions.create(self._engine)
                with self._engine.begin() as conn:
                    conn.execute(text(
                        "INSERT INTO positions"
                        " (account, symbol, quantity, entry_price, stop_loss, take_profit, opened_at)"
                        f" SELECT {acct}, symbol, quantity, entry_price, stop_loss, take_profit, opened_at"
                        " FROM positions_legacy"
                    ))
                    conn.execute(text("DROP TABLE positions_legacy"))
        # Agrega columnas ai_* a decisions (si les falta, quedan NULL en filas viejas).
        if "decisions" in existing:
            cols = {c["name"] for c in inspect(self._engine).get_columns("decisions")}
            for col, typedef in [
                ("ai_action", "TEXT"),
                ("ai_confidence", "REAL"),
                ("ai_rationale", "TEXT"),
            ]:
                if col not in cols:
                    with self._engine.begin() as conn:
                        conn.execute(text(
                            f"ALTER TABLE decisions ADD COLUMN {col} {typedef}"
                        ))

    def _migrate_accounts(self) -> None:
        # Agrega ai_provider / ai_model a accounts si faltan (DB sembrada antes del soporte
        # multi-proveedor). ADD COLUMN con DEFAULT constante backfillea las filas viejas y
        # es compatible con SQLite y Postgres (por eso no se restringe a un dialecto).
        insp = inspect(self._engine)
        if "accounts" not in set(insp.get_table_names()):
            return
        cols = {c["name"] for c in insp.get_columns("accounts")}
        for col, default in (("ai_provider", "anthropic"), ("ai_model", "claude-haiku-4-5")):
            if col in cols:
                continue
            try:
                with self._engine.begin() as conn:
                    conn.execute(text(
                        f"ALTER TABLE accounts ADD COLUMN {col} TEXT NOT NULL DEFAULT '{default}'"
                    ))
            except Exception:  # noqa: BLE001 - tolera carrera / migración repetida
                # Otra instancia pudo agregar la columna entre el inspect y el ALTER (o se
                # reejecuta la migración): si ya existe es un no-op; si no, es un error real.
                fresh = {c["name"] for c in inspect(self._engine).get_columns("accounts")}
                if col not in fresh:
                    raise

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

    # ---- fills ----
    def record_fill(self, account: str, ts: str, fill: Fill) -> None:
        with self._engine.begin() as conn:
            conn.execute(insert(fills).values(
                account=account, ts=ts, symbol=fill.symbol, side=fill.side.value,
                quantity=fill.quantity, price=fill.price, fee=fill.fee,
            ))

    def recent_fills(self, account: str, limit: int = 50) -> list[dict]:
        stmt = (
            select(fills.c.ts, fills.c.symbol, fills.c.side,
                   fills.c.quantity, fills.c.price, fills.c.fee)
            .where(fills.c.account == account)
            .order_by(fills.c.id.desc())
            .limit(limit)
        )
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    # ---- posiciones (upsert cross-DB: update y si no afecta filas, insert) ----
    def upsert_position(self, account: str, pos: Position, opened_at: str) -> None:
        values = dict(
            quantity=pos.quantity, entry_price=pos.entry_price,
            stop_loss=pos.stop_loss, take_profit=pos.take_profit,
        )
        with self._engine.begin() as conn:
            res = conn.execute(
                update(positions)
                .where(positions.c.account == account, positions.c.symbol == pos.symbol)
                .values(**values)
            )
            if res.rowcount == 0:
                conn.execute(insert(positions).values(
                    account=account, symbol=pos.symbol, opened_at=opened_at, **values,
                ))

    def remove_position(self, account: str, symbol: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                delete(positions)
                .where(positions.c.account == account, positions.c.symbol == symbol)
            )

    def get_positions(self, account: str) -> dict[str, Position]:
        stmt = select(
            positions.c.symbol, positions.c.quantity, positions.c.entry_price,
            positions.c.stop_loss, positions.c.take_profit,
        ).where(positions.c.account == account)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return {
            r.symbol: Position(r.symbol, r.quantity, r.entry_price, r.stop_loss, r.take_profit)
            for r in rows
        }

    # ---- accounts ----
    def upsert_account(
        self, id: str, name: str, strategy: str, symbol: str, timeframe: str,
        interval_seconds: int, starting_cash: float, ai_enabled: bool,
        enabled: bool, params: dict,
        ai_provider: str = "anthropic", ai_model: str = "claude-haiku-4-5",
    ) -> None:
        values = dict(
            name=name, strategy=strategy, symbol=symbol, timeframe=timeframe,
            interval_seconds=interval_seconds, starting_cash=starting_cash,
            ai_enabled=ai_enabled, enabled=enabled, params=params,
            ai_provider=ai_provider, ai_model=ai_model,
        )
        with self._engine.begin() as conn:
            res = conn.execute(
                update(accounts).where(accounts.c.id == id).values(**values)
            )
            if res.rowcount == 0:
                conn.execute(insert(accounts).values(id=id, **values))

    def list_accounts(self) -> list[dict]:
        stmt = select(accounts).order_by(accounts.c.id)
        with self._engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(stmt)]

    def get_account(self, id: str) -> dict | None:
        stmt = select(accounts).where(accounts.c.id == id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()
        return None if row is None else dict(row._mapping)

    def set_account_enabled(self, id: str, enabled: bool) -> None:
        with self._engine.begin() as conn:
            conn.execute(update(accounts).where(accounts.c.id == id).values(enabled=enabled))

    def close(self) -> None:
        self._engine.dispose()
