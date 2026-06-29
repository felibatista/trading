from __future__ import annotations

import os
from collections.abc import Iterator

from fastapi import Depends

from bot.config import Config, load_config
from bot.store.db import Store

CONFIG_PATH = os.environ.get("AMERICO_CONFIG", "config.yaml")


def get_config() -> Config:
    return load_config(CONFIG_PATH)


def get_store(config: Config = Depends(get_config)) -> Iterator[Store]:
    store = Store(config.db_path)
    try:
        yield store
    finally:
        store.close()
