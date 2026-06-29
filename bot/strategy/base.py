from __future__ import annotations

from typing import Callable

import pandas as pd

from bot.models import Signal

StrategyFn = Callable[[pd.DataFrame, dict], Signal]
