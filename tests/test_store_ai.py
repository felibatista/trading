import sqlite3

from bot.store.db import Store


def test_record_decision_persists_ai_fields():
    s = Store(":memory:")
    s.record_decision(
        "default", "t1", "BTC/USDT", "BUY", "cruce", 3.0, 2.0, 40.0,
        ai_action="HOLD", ai_confidence=0.42, ai_rationale="señales débiles",
    )
    d = s.recent_decisions("default", limit=1)[0]
    assert d["ai_action"] == "HOLD"
    assert d["ai_confidence"] == 0.42
    assert d["ai_rationale"] == "señales débiles"


def test_record_decision_ai_fields_default_to_none():
    s = Store(":memory:")
    s.record_decision("default", "t1", "BTC/USDT", "BUY", "cruce", 3.0, 2.0, 40.0)
    d = s.recent_decisions("default", limit=1)[0]
    assert d["ai_action"] is None
    assert d["ai_confidence"] is None
    assert d["ai_rationale"] is None


def test_migrates_existing_db_without_ai_columns(tmp_path):
    db = tmp_path / "old.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE decisions ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " ts TEXT, symbol TEXT, action TEXT, reason TEXT,"
        " ema_fast REAL, ema_slow REAL, rsi REAL);"
    )
    conn.execute(
        "INSERT INTO decisions (ts,symbol,action,reason,ema_fast,ema_slow,rsi)"
        " VALUES ('t0','BTC/USDT','HOLD','viejo',1.0,2.0,50.0)"
    )
    conn.commit()
    conn.close()

    s = Store(str(db))  # al abrir debe migrar agregando columnas ai_* y account
    rows = s.recent_decisions("default", limit=10)
    assert rows[-1]["reason"] == "viejo"
    assert rows[-1]["ai_action"] is None  # fila vieja queda con ai_* en NULL

    s.record_decision(
        "default", "t1", "BTC/USDT", "BUY", "nuevo", 3.0, 2.0, 40.0,
        ai_action="BUY", ai_confidence=0.9, ai_rationale="ok",
    )
    assert s.recent_decisions("default", limit=1)[0]["ai_confidence"] == 0.9
