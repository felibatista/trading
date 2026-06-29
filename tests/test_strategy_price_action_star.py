from __future__ import annotations

import pandas as pd

from bot.models import Action
from bot.strategy.price_action import decide_price_action


def test_shooting_star_sells():
    # Vela previa neutra; última con mecha superior larga y cuerpo chico -> SELL.
    rows = [(10, 10.5, 9.5, 10), (10.0, 11.0, 9.95, 10.05)]
    # cuerpo 0.05, mecha sup = 11.0 - 10.05 = 0.95 (>= 2*cuerpo), mecha inf = 9.95 baja poco
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(range(len(rows)), unit="ms", utc=True),
        "open": [r[0] for r in rows], "high": [r[1] for r in rows],
        "low": [r[2] for r in rows], "close": [r[3] for r in rows], "volume": [1] * len(rows),
    })
    sig = decide_price_action(df, {"wick_ratio": 2.0})
    assert sig.action is Action.SELL
