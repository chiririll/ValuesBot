from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VALUES_PATH = PROJECT_ROOT / "data" / "values.json"
DEFAULT_DB_PATH = PROJECT_ROOT / "sessions.db"


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    values_path: Path
    db_path: Path


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Copy example.env to .env and fill in the token.")
    return Settings(
        bot_token=token,
        values_path=DEFAULT_VALUES_PATH,
        db_path=DEFAULT_DB_PATH,
    )
