from __future__ import annotations

import pandas as pd

from bot.indicators import bollinger


def test_bollinger_bands_ordered():
    s = pd.Series([10.0, 11, 9, 12, 8, 13, 7, 14, 6, 15, 5, 16])
    mid, upper, lower = bollinger(s, period=4, num_std=2.0)
    tail = slice(4, None)
    assert (upper[tail] >= mid[tail]).all()
    assert (mid[tail] >= lower[tail]).all()
