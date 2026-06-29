from __future__ import annotations

import pandas as pd

from bot.indicators import macd


def test_macd_shapes_and_relation():
    s = pd.Series([float(i) for i in range(40)])
    line, signal, hist = macd(s, fast=3, slow=6, signal=2)
    assert len(line) == len(signal) == len(hist) == 40
    # hist == line - signal (donde no hay NaN)
    assert abs((hist - (line - signal)).dropna().abs().max()) < 1e-9
