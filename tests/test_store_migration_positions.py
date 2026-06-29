from __future__ import annotations

import sqlite3

from bot.broker.models import Position
from bot.store.db import Store


def test_migrated_positions_allow_same_symbol_across_accounts(tmp_path):
    # DB vieja: positions con PK de un solo campo (symbol), como el esquema original.
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE positions (symbol TEXT PRIMARY KEY, quantity REAL, entry_price REAL,"
        " stop_loss REAL, take_profit REAL, opened_at TEXT);"
        "INSERT INTO positions VALUES ('BTC/USDT', 0.5, 100.0, 98.0, 104.0, '2026-01-01T00:00:00+00:00');"
    )
    con.commit()
    con.close()

    s = Store(str(db))
    # La fila vieja quedó bajo account='default'.
    assert s.get_positions("default")["BTC/USDT"].quantity == 0.5
    # Otra cuenta puede abrir el MISMO símbolo sin IntegrityError (PK compuesta).
    s.upsert_position(
        "scalper", Position("BTC/USDT", 0.7, 200.0, 196.0, 208.0),
        "2026-01-01T00:01:00+00:00",
    )
    assert s.get_positions("scalper")["BTC/USDT"].quantity == 0.7
    assert s.get_positions("default")["BTC/USDT"].quantity == 0.5  # no se pisó
    s.close()


def test_migration_is_idempotent_on_reopen(tmp_path):
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE positions (symbol TEXT PRIMARY KEY, quantity REAL, entry_price REAL,"
        " stop_loss REAL, take_profit REAL, opened_at TEXT);"
        "INSERT INTO positions VALUES ('ETH/USDT', 1.0, 50.0, 49.0, 52.0, '2026-01-01T00:00:00+00:00');"
    )
    con.commit()
    con.close()

    Store(str(db)).close()       # primera migración (reconstruye positions)
    s = Store(str(db))           # reabrir: ya tiene PK compuesta, no debe romper ni duplicar
    assert s.get_positions("default")["ETH/USDT"].quantity == 1.0
    s.close()
