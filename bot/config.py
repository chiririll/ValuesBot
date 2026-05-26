from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VALUES_PATH = Path("res", "values.json")
DEFAULT_DB_PATH = Path("data", "sessions.db")


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    values_path: Path
    db_path: Path


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    if not DEFAULT_VALUES_PATH.exists():
        raise FileNotFoundError(f"Values file not found at {DEFAULT_VALUES_PATH}")

    return Settings(
        bot_token=token,
        values_path=DEFAULT_VALUES_PATH,
        db_path=DEFAULT_DB_PATH,
    )
