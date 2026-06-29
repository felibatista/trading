from __future__ import annotations

from sqlalchemy import inspect

from bot.store.engine import make_engine
from bot.store.schema import metadata


def test_create_all_makes_tables():
    eng = make_engine(":memory:")
    metadata.create_all(eng)
    names = set(inspect(eng).get_table_names())
    assert {"decisions", "fills", "positions", "equity", "accounts"} <= names


def test_account_columns_present():
    eng = make_engine(":memory:")
    metadata.create_all(eng)
    insp = inspect(eng)
    for table in ("decisions", "fills", "positions", "equity"):
        cols = {c["name"] for c in insp.get_columns(table)}
        assert "account" in cols, f"falta account en {table}"
