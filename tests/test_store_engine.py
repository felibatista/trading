from __future__ import annotations

import os

from sqlalchemy import Engine, text

from bot.store.engine import make_engine, normalize_url


def test_memory_engine_is_sqlite():
    eng = make_engine(":memory:")
    assert isinstance(eng, Engine)
    assert eng.dialect.name == "sqlite"
    with eng.connect() as c:
        assert c.execute(text("select 1")).scalar() == 1


def test_path_becomes_sqlite_url(tmp_path):
    eng = make_engine(str(tmp_path / "x.sqlite"))
    assert eng.dialect.name == "sqlite"


def test_database_url_env_overrides(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    eng = make_engine("ignored.sqlite")
    assert eng.dialect.name == "sqlite"


def test_postgres_url_normalized_to_psycopg3():
    # Coolify entrega postgres://... — debe forzar el driver psycopg 3.
    assert normalize_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"
