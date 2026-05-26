from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bot.db._sql_loader import load_migrations
from bot.db.sessions_repo import SessionsRepository


@pytest.mark.asyncio
async def test_init_idempotent(repo: SessionsRepository) -> None:
    await repo.init()


@pytest.mark.asyncio
async def test_save_and_load(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json='{"stages": {}}',
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    session = await repo.load(1)
    assert session is not None
    assert session.comparisons_done == 0


@pytest.mark.asyncio
async def test_save_updates(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.save(
        1,
        state_json="v2",
        prev_state_json="v1",
        comparisons_done=1,
        estimated_total=10,
    )
    session = await repo.load(1)
    assert session is not None
    assert session.state_json == "v2"
    assert session.comparisons_done == 1


@pytest.mark.asyncio
async def test_undo_restores(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v2",
        prev_state_json="v1",
        comparisons_done=2,
        estimated_total=10,
    )
    session = await repo.undo(1)
    assert session is not None
    assert session.state_json == "v1"
    assert session.prev_state_json is None
    assert session.comparisons_done == 1


@pytest.mark.asyncio
async def test_undo_without_prev(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    session = await repo.undo(1)
    assert session is not None
    assert session.state_json == "v1"


@pytest.mark.asyncio
async def test_finish(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=5,
        estimated_total=10,
    )
    await repo.finish(
        1,
        state_json="v1",
        comparisons_done=5,
        estimated_total=10,
        result_json='{"terminal": {}}',
    )
    session = await repo.load(1)
    assert session is not None
    assert session.is_finished
    assert session.result_json is not None


@pytest.mark.asyncio
async def test_delete(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.delete(1)
    assert await repo.load(1) is None


@pytest.mark.asyncio
async def test_update_last_question_message(repo: SessionsRepository) -> None:
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.update_last_question_message(1, chat_id=100, message_id=200)
    session = await repo.load(1)
    assert session is not None
    assert session.last_question_chat_id == 100
    assert session.last_question_message_id == 200


@pytest.mark.asyncio
async def test_init_recovers_pre_migration_schema(tmp_path: Path) -> None:
    """Older databases lack the last_question_* columns; init() must upgrade
    them transparently so subsequent saves/loads work."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    try:
        first_migration = load_migrations()[0]
        conn.executescript(first_migration)
        conn.commit()
    finally:
        conn.close()

    repo = SessionsRepository(db_path)
    await repo.init()
    await repo.save(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.update_last_question_message(1, chat_id=42, message_id=43)
    session = await repo.load(1)
    await repo.close()

    assert session is not None
    assert session.last_question_chat_id == 42
    assert session.last_question_message_id == 43
