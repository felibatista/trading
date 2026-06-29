from __future__ import annotations

import sqlite3

from bot.broker.models import Fill, Position

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, symbol TEXT, action TEXT, reason TEXT,
    ema_fast REAL, ema_slow REAL, rsi REAL
);
CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, symbol TEXT, side TEXT, quantity REAL, price REAL, fee REAL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity REAL, entry_price REAL, stop_loss REAL, take_profit REAL, opened_at TEXT
);
CREATE TABLE IF NOT EXISTS equity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT, equity REAL, cash REAL
);
"""


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    def record_decision(
        self, ts: str, symbol: str, action: str, reason: str,
        ema_fast: float, ema_slow: float, rsi: float,
    ) -> None:
        self._conn.execute(
            "INSERT INTO decisions (ts,symbol,action,reason,ema_fast,ema_slow,rsi)"
            " VALUES (?,?,?,?,?,?,?)",
            (ts, symbol, action, reason, ema_fast, ema_slow, rsi),
        )
        self._conn.commit()

    def recent_decisions(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,symbol,action,reason,ema_fast,ema_slow,rsi FROM decisions"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def record_fill(self, ts: str, fill: Fill) -> None:
        self._conn.execute(
            "INSERT INTO fills (ts,symbol,side,quantity,price,fee) VALUES (?,?,?,?,?,?)",
            (ts, fill.symbol, fill.side.value, fill.quantity, fill.price, fill.fee),
        )
        self._conn.commit()

    def upsert_position(self, pos: Position, opened_at: str) -> None:
        self._conn.execute(
            "INSERT INTO positions (symbol,quantity,entry_price,stop_loss,take_profit,opened_at)"
            " VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(symbol) DO UPDATE SET"
            " quantity=excluded.quantity, entry_price=excluded.entry_price,"
            " stop_loss=excluded.stop_loss, take_profit=excluded.take_profit",
            (pos.symbol, pos.quantity, pos.entry_price, pos.stop_loss, pos.take_profit, opened_at),
        )
        self._conn.commit()

    def remove_position(self, symbol: str) -> None:
        self._conn.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
        self._conn.commit()

    def get_positions(self) -> dict[str, Position]:
        rows = self._conn.execute(
            "SELECT symbol,quantity,entry_price,stop_loss,take_profit FROM positions"
        ).fetchall()
        return {
            r["symbol"]: Position(
                r["symbol"], r["quantity"], r["entry_price"], r["stop_loss"], r["take_profit"]
            )
            for r in rows
        }

    def record_equity(self, ts: str, equity: float, cash: float) -> None:
        self._conn.execute(
            "INSERT INTO equity (ts,equity,cash) VALUES (?,?,?)", (ts, equity, cash)
        )
        self._conn.commit()

    def latest_equity(self) -> tuple[float, float] | None:
        row = self._conn.execute(
            "SELECT equity,cash FROM equity ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else (row["equity"], row["cash"])

    def equity_series(self, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,equity,cash FROM equity ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def recent_fills(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts,symbol,side,quantity,price,fee FROM fills"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
