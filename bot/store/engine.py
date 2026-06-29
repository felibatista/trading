from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool


def normalize_url(url: str) -> str:
    """Fuerza el driver psycopg 3 en URLs de Postgres (Coolify da postgres://...)."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def make_engine(target: str = ":memory:") -> Engine:
    """Devuelve un Engine de SQLAlchemy.

    - Si DATABASE_URL está seteada, se usa esa URL (Postgres en Coolify).
    - Si `target` ya es una URL (contiene '://'), se usa tal cual.
    - ":memory:" -> SQLite en memoria con pool estático (compartible entre hilos).
    - Cualquier otra cosa se interpreta como path de archivo SQLite.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        return create_engine(normalize_url(url), future=True)
    if "://" in target:
        return create_engine(normalize_url(target), future=True)
    if target == ":memory:":
        return create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        f"sqlite:///{target}",
        future=True,
        connect_args={"check_same_thread": False},
    )
