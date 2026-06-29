import pandas as pd
import pytest


def make_df(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * n,
        }
    )


@pytest.fixture
def uptrend_df() -> pd.DataFrame:
    return make_df([float(x) for x in range(1, 81)])
