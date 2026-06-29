from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.deps import CONFIG_PATH, get_config, get_store
from bot.ai.advisor import DEFAULT_MODEL_BY_PROVIDER
from api.models import (
    AccountOut,
    AccountUpdate,
    BacktestPoint,
    BacktestRequest,
    BacktestResultOut,
    CandleOut,
    DecisionOut,
    EquityPoint,
    FillOut,
    PositionOut,
    StatusResponse,
    StrategyOut,
)
from bot.accounts import DEFAULT_ACCOUNTS, seed_default_accounts
from bot.backtest.data import load_ohlcv_range
from bot.backtest.report import resolve_window
from bot.backtest.runner import run_fleet_backtest
from bot.config import Config, load_config
from bot.data.feed import CcxtDataFeed, DataFeed, make_ccxt_exchange
from bot.fleet import Fleet
from bot.store.db import Store

logger = logging.getLogger(__name__)

# Feed compartido a nivel módulo (singleton lazy): un solo exchange para todo el
# proceso, en vez de construir uno por request. Es seteable/override-able para
# los tests vía set_candle_feed() o app.dependency_overrides[get_candle_feed].
_candle_feed: DataFeed | None = None

# Cache TTL en proceso para no golpear el exchange con el polling del panel.
# Mantenerlo >= el intervalo de polling del panel (2.5s) para deduplicar de verdad.
_CANDLE_TTL_SECONDS = 4.0
_candle_cache: dict[tuple, tuple[float, list[CandleOut]]] = {}


def set_candle_feed(feed: DataFeed | None) -> None:
    """Reemplaza el feed compartido (principalmente para tests). Limpia el cache."""
    global _candle_feed
    _candle_feed = feed
    _candle_cache.clear()


def get_candle_feed(config: Config = Depends(get_config)) -> DataFeed:
    """Devuelve el feed compartido, creándolo de forma lazy si no existe."""
    global _candle_feed
    if _candle_feed is None:
        _candle_feed = CcxtDataFeed(exchange_id=config.exchange)
    return _candle_feed


# ── Backtest ────────────────────────────────────────────────────────────────
# Exchange ccxt (singleton lazy) para el fetch histórico, y cache de velas por
# (símbolo, timeframe, ventana redondeada a 5') para que re-correr sea rápido.
# Ambos override-ables para tests vía set_backtest_exchange / dependency_overrides.
_backtest_exchange = None
_BACKTEST_BUCKET_MS = 300_000
_backtest_cache: dict[tuple, object] = {}


def set_backtest_exchange(exchange) -> None:
    global _backtest_exchange
    _backtest_exchange = exchange
    _backtest_cache.clear()


def get_backtest_exchange(config: Config = Depends(get_config)):
    global _backtest_exchange
    if _backtest_exchange is None:
        _backtest_exchange = make_ccxt_exchange(config.exchange)
    return _backtest_exchange


def get_backtest_advisor_factory():
    # Default: el factory real. Tests lo overridean con un stub determinístico.
    from bot.cli import make_advisor

    return make_advisor


def _cached_candles(exchange, symbol: str, timeframe: str, since_ms: int, until_ms: int):
    key = (symbol, timeframe, since_ms // _BACKTEST_BUCKET_MS, until_ms // _BACKTEST_BUCKET_MS)
    if key not in _backtest_cache:
        _backtest_cache[key] = load_ohlcv_range(exchange, symbol, timeframe, since_ms, until_ms)
    return _backtest_cache[key]


def _downsample_curve(curve: list[dict], max_points: int = 300) -> list[BacktestPoint]:
    if not curve:
        return []
    # Muestrea a <= max_points-1 (ceil division) y agrega el último → total <= max_points.
    target = max(1, max_points - 1)
    step = max(1, -(-len(curve) // target))
    sampled = list(curve[::step])
    if sampled[-1]["ts"] != curve[-1]["ts"]:
        sampled.append(curve[-1])
    return [BacktestPoint(ts=p["ts"], equity=p["equity"]) for p in sampled]


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "AMERICO_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def _make_lifespan():
    @asynccontextmanager
    async def lifespan(app):
        fleet = None
        if os.environ.get("AMERICO_RUN_FLEET", "0") == "1":
            config = load_config(CONFIG_PATH)
            store = Store(config.db_path)
            seed_default_accounts(store)
            fleet = Fleet(store, config)
            fleet.start()
        try:
            yield
        finally:
            if fleet is not None:
                fleet.stop()
    return lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="AMÉRICO API", version="2.0.0", lifespan=_make_lifespan())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status", response_model=StatusResponse)
    def status(
        account: str = "default",
        config: Config = Depends(get_config),
        store: Store = Depends(get_store),
    ) -> StatusResponse:
        eq = store.latest_equity(account)
        equity, cash = eq if eq is not None else (0.0, 0.0)

        recent = store.recent_decisions(account, 1)
        last_run_at = recent[0]["ts"] if recent else None
        next_run_at: str | None = None
        if last_run_at is not None:
            try:
                next_run_at = (
                    datetime.fromisoformat(last_run_at)
                    + timedelta(seconds=config.loop_interval_seconds)
                ).isoformat()
            except ValueError:
                # ts no-ISO (datos legacy/manuales): no rompemos el header del panel.
                next_run_at = None

        s = config.strategy
        return StatusResponse(
            exchange=config.exchange,
            timeframe=config.timeframe,
            broker_kind=config.broker.kind,
            symbols=config.symbols,
            equity=equity,
            cash=cash,
            loop_interval_seconds=config.loop_interval_seconds,
            last_run_at=last_run_at,
            next_run_at=next_run_at,
            strategy=StrategyOut(
                fast=s.fast,
                slow=s.slow,
                rsi_period=s.rsi_period,
                rsi_oversold=s.rsi_oversold,
                rsi_overbought=s.rsi_overbought,
            ),
        )

    @app.get("/api/candles", response_model=list[CandleOut])
    def candles(
        symbol: str | None = None,
        timeframe: str | None = None,
        limit: int = 120,
        config: Config = Depends(get_config),
        feed: DataFeed = Depends(get_candle_feed),
    ) -> list[CandleOut]:
        sym = symbol or config.symbols[0]
        tf = timeframe or config.timeframe
        lim = max(1, min(limit, 500))

        key = (id(feed), sym, tf, lim)
        now = time.monotonic()
        cached = _candle_cache.get(key)
        if cached is not None and (now - cached[0]) < _CANDLE_TTL_SECONDS:
            return cached[1]

        try:
            # Incluimos la última vela (en formación): NO usamos drop_forming_candle
            # para que el gráfico sea vivo.
            df = feed.fetch_ohlcv(sym, tf, lim)
            out = [
                CandleOut(
                    ts=row.timestamp.isoformat(),
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=float(row.volume),
                )
                for row in df.itertuples(index=False)
            ]
        except Exception:
            # Ante cualquier error de red/exchange, el panel debe seguir vivo.
            logger.exception("candles: fallo al traer OHLCV para %s %s", sym, tf)
            return []

        _candle_cache[key] = (now, out)
        return out

    @app.get("/api/equity", response_model=list[EquityPoint])
    def equity(limit: int = 200, account: str = "default", store: Store = Depends(get_store)) -> list[EquityPoint]:
        return [EquityPoint(**row) for row in store.equity_series(account, limit)]

    @app.get("/api/positions", response_model=list[PositionOut])
    def positions(account: str = "default", store: Store = Depends(get_store)) -> list[PositionOut]:
        return [
            PositionOut(
                symbol=p.symbol,
                quantity=p.quantity,
                entry_price=p.entry_price,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
            )
            for p in store.get_positions(account).values()
        ]

    @app.get("/api/decisions", response_model=list[DecisionOut])
    def decisions(limit: int = 20, account: str = "default", store: Store = Depends(get_store)) -> list[DecisionOut]:
        return [DecisionOut(**row) for row in store.recent_decisions(account, limit)]

    @app.get("/api/fills", response_model=list[FillOut])
    def fills(limit: int = 50, account: str = "default", store: Store = Depends(get_store)) -> list[FillOut]:
        return [FillOut(**row) for row in store.recent_fills(account, limit)]

    @app.get("/api/accounts", response_model=list[AccountOut])
    def accounts_list(store: Store = Depends(get_store)) -> list[AccountOut]:
        out: list[AccountOut] = []
        for a in store.list_accounts():
            eq = store.latest_equity(a["id"])
            equity_v, cash = eq if eq is not None else (a["starting_cash"], a["starting_cash"])
            out.append(AccountOut(
                id=a["id"], name=a["name"], strategy=a["strategy"], symbol=a["symbol"],
                timeframe=a["timeframe"], interval_seconds=a["interval_seconds"],
                ai_enabled=a["ai_enabled"], ai_provider=a["ai_provider"],
                ai_model=a["ai_model"], enabled=a["enabled"],
                starting_cash=a["starting_cash"],
                equity=equity_v, cash=cash,
            ))
        return out

    @app.put("/api/accounts/{account_id}", response_model=AccountOut)
    def update_account(
        account_id: str, patch: AccountUpdate, store: Store = Depends(get_store),
    ) -> AccountOut:
        current = store.get_account(account_id)
        if current is None:
            raise HTTPException(status_code=404, detail="cuenta no encontrada")
        pd = patch.model_dump(exclude_none=True)
        data = {**current, **pd}
        # Si se cambia de proveedor sin mandar modelo, reseteamos al default del nuevo
        # (espeja changeProvider del panel): evita un par provider/model incompatible que
        # dejaría la IA en solo-reglas en silencio para callers REST/scripts.
        if "ai_provider" in pd and "ai_model" not in pd:
            data["ai_model"] = DEFAULT_MODEL_BY_PROVIDER.get(data["ai_provider"], data["ai_model"])
        store.upsert_account(
            account_id, data["name"], data["strategy"], data["symbol"],
            data["timeframe"], data["interval_seconds"], data["starting_cash"],
            data["ai_enabled"], data["enabled"], data["params"],
            data["ai_provider"], data["ai_model"],
        )
        eq = store.latest_equity(account_id)
        equity_v, cash = eq if eq is not None else (data["starting_cash"], data["starting_cash"])
        return AccountOut(
            id=account_id, name=data["name"], strategy=data["strategy"],
            symbol=data["symbol"], timeframe=data["timeframe"],
            interval_seconds=data["interval_seconds"], ai_enabled=data["ai_enabled"],
            ai_provider=data["ai_provider"], ai_model=data["ai_model"],
            enabled=data["enabled"], equity=equity_v, cash=cash,
            starting_cash=data["starting_cash"],
        )

    @app.post("/api/backtest", response_model=list[BacktestResultOut])
    def backtest(
        req: BacktestRequest,
        config: Config = Depends(get_config),
        exchange=Depends(get_backtest_exchange),
        advisor_factory=Depends(get_backtest_advisor_factory),
    ) -> list[BacktestResultOut]:
        symbol = req.symbol or DEFAULT_ACCOUNTS[0]["symbol"]
        accounts = [{**a, "symbol": symbol} for a in DEFAULT_ACCOUNTS]
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        since_ms, until_ms = resolve_window(now_ms, days=req.days, from_=req.from_, to=req.to)
        tfs = sorted({a["timeframe"] for a in accounts})
        try:
            candles_by_tf = {
                tf: _cached_candles(exchange, symbol, tf, since_ms, until_ms) for tf in tfs
            }
        except Exception as exc:  # noqa: BLE001 - error claro en vez de 500 crudo
            raise HTTPException(status_code=502, detail=f"no se pudieron bajar datos: {exc}")
        results = run_fleet_backtest(
            accounts, candles_by_tf, risk=config.risk,
            fee_rate=config.broker.fee_rate, slippage=config.broker.slippage,
            advisor_factory=advisor_factory,
        )
        return [
            BacktestResultOut(
                account_id=r.account_id, name=r.name, strategy=r.strategy, ai=r.ai,
                return_pct=r.return_pct, max_drawdown_pct=r.max_drawdown_pct,
                win_rate=r.win_rate, num_trades=r.num_trades, final_equity=r.final_equity,
                exposure=r.exposure, equity_curve=_downsample_curve(r.equity_curve),
            )
            for r in results
        ]

    web_dist = os.environ.get("AMERICO_WEB_DIST", "web_dist")
    assets = os.path.join(web_dist, "assets")
    index = os.path.join(web_dist, "index.html")
    if os.path.isdir(web_dist) and os.path.isfile(index):
        if os.path.isdir(assets):
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            if full_path == "api" or full_path.startswith("api/"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            return FileResponse(index)

    return app


app = create_app()
