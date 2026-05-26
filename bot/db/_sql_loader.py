"""Tiny helper that loads SQL statements from ``bot/db/sql``.

Keeping SQL in dedicated ``.sql`` files makes the queries easier to read,
diff, and lint with external tools (sqlfluff, IDE SQL plugins).
"""

from __future__ import annotations

from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"
MIGRATIONS_DIR = SQL_DIR / "migrations"


def load_sql(name: str) -> str:
    return (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")


def load_migrations() -> tuple[str, ...]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return tuple(path.read_text(encoding="utf-8") for path in files)
