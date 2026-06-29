# tests/test_store_migration.py
from __future__ import annotations

import sqlite3

from bot.store.db import Store


def test_legacy_sqlite_rows_get_default_account(tmp_path):
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE equity (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, equity REAL, cash REAL);"
        "INSERT INTO equity (ts, equity, cash) VALUES ('2026-01-01T00:00:00+00:00', 10000.0, 10000.0);"
    )
    con.commit()
    con.close()

    s = Store(str(db))
    assert s.latest_equity("default") == (10000.0, 10000.0)
    s.close()
