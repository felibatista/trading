from bot.cli import run_decide
from bot.config import Config
from bot.models import Action


class FakeFeed:
    def __init__(self, df):
        self._df = df

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self._df


def test_run_decide_returns_signal_from_feed(uptrend_df):
    sig = run_decide(FakeFeed(uptrend_df), Config(), "BTC/USDT", "1h")
    assert isinstance(sig.action, Action)
    assert set(sig.indicators) == {"ema_fast", "ema_slow", "rsi"}
