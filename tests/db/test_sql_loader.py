"""Tests for the SQL loader contract.

These tests exercise ``load_sql`` and ``load_migrations`` as functions
without peeking into the underlying directory layout — that's the loader's
private implementation detail.
"""

from __future__ import annotations

import pytest

from bot.db._sql_loader import load_migrations, load_sql


def test_load_sql_returns_text_for_known_query() -> None:
    sql = load_sql("load_session_by_user")
    assert isinstance(sql, str)
    assert sql.strip(), "expected non-empty SQL text"


def test_load_sql_unknown_name_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_sql("definitely_not_a_real_query_name")


def test_load_migrations_returns_strings() -> None:
    migrations = load_migrations()
    assert isinstance(migrations, tuple)
    assert all(isinstance(text, str) and text.strip() for text in migrations)


def test_load_migrations_is_deterministic() -> None:
    first = load_migrations()
    second = load_migrations()
    assert first == second
