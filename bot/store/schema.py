# bot/store/schema.py
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
)

metadata = MetaData()

decisions = Table(
    "decisions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("ema_fast", Float),
    Column("ema_slow", Float),
    Column("rsi", Float),
    Column("ai_action", Text),
    Column("ai_confidence", Float),
    Column("ai_rationale", Text),
)

fills = Table(
    "fills", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("quantity", Float, nullable=False),
    Column("price", Float, nullable=False),
    Column("fee", Float, nullable=False),
)

positions = Table(
    "positions", metadata,
    Column("account", Text, primary_key=True),
    Column("symbol", Text, primary_key=True),
    Column("quantity", Float, nullable=False),
    Column("entry_price", Float, nullable=False),
    Column("stop_loss", Float, nullable=False),
    Column("take_profit", Float, nullable=False),
    Column("opened_at", Text, nullable=False),
)

equity = Table(
    "equity", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account", Text, nullable=False, index=True),
    Column("ts", Text, nullable=False),
    Column("equity", Float, nullable=False),
    Column("cash", Float, nullable=False),
)

accounts = Table(
    "accounts", metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("strategy", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("timeframe", Text, nullable=False),
    Column("interval_seconds", Integer, nullable=False),
    Column("starting_cash", Float, nullable=False),
    Column("ai_enabled", Boolean, nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("params", JSON, nullable=False),
)
