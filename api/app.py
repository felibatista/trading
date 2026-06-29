from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_config, get_store
from api.models import DecisionOut, EquityPoint, FillOut, PositionOut, StatusResponse
from bot.config import Config
from bot.store.db import Store


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "AMERICO_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    app = FastAPI(title="AMÉRICO API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status", response_model=StatusResponse)
    def status(
        config: Config = Depends(get_config),
        store: Store = Depends(get_store),
    ) -> StatusResponse:
        eq = store.latest_equity()
        equity, cash = eq if eq is not None else (0.0, 0.0)
        return StatusResponse(
            exchange=config.exchange,
            timeframe=config.timeframe,
            broker_kind=config.broker.kind,
            symbols=config.symbols,
            equity=equity,
            cash=cash,
        )

    @app.get("/api/equity", response_model=list[EquityPoint])
    def equity(limit: int = 200, store: Store = Depends(get_store)) -> list[EquityPoint]:
        return [EquityPoint(**row) for row in store.equity_series(limit)]

    @app.get("/api/positions", response_model=list[PositionOut])
    def positions(store: Store = Depends(get_store)) -> list[PositionOut]:
        return [
            PositionOut(
                symbol=p.symbol,
                quantity=p.quantity,
                entry_price=p.entry_price,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
            )
            for p in store.get_positions().values()
        ]

    @app.get("/api/decisions", response_model=list[DecisionOut])
    def decisions(limit: int = 20, store: Store = Depends(get_store)) -> list[DecisionOut]:
        return [DecisionOut(**row) for row in store.recent_decisions(limit)]

    @app.get("/api/fills", response_model=list[FillOut])
    def fills(limit: int = 50, store: Store = Depends(get_store)) -> list[FillOut]:
        return [FillOut(**row) for row in store.recent_fills(limit)]

    return app


app = create_app()
