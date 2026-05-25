from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALUES_PATH = PROJECT_ROOT / "data" / "values.txt"
DB_PATH = PROJECT_ROOT / "sessions.db"

BOT_TOKEN = os.getenv("BOT_TOKEN")


def require_bot_token() -> str:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill in the token.")
    return BOT_TOKEN
