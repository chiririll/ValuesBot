from __future__ import annotations

import aiosqlite
import pytest

from bot.db.sessions_repo import SessionsRepository


@pytest.mark.asyncio
async def test_init_idempotent(repo: SessionsRepository) -> None:
    await repo.init()


@pytest.mark.asyncio
async def test_create_and_load_active(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json='{"stages": {}}',
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    loaded = await repo.load_active(1)
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.comparisons_done == 0


@pytest.mark.asyncio
async def test_create_rejects_duplicate_active(repo: SessionsRepository) -> None:
    await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    with pytest.raises(aiosqlite.IntegrityError):
        await repo.create(
            1,
            state_json="v2",
            prev_state_json=None,
            comparisons_done=0,
            estimated_total=10,
        )


@pytest.mark.asyncio
async def test_save_updates(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.save(
        session.id,
        state_json="v2",
        prev_state_json="v1",
        comparisons_done=1,
        estimated_total=10,
        question_id=2,
    )
    loaded = await repo.load_by_id(session.id)
    assert loaded is not None
    assert loaded.state_json == "v2"
    assert loaded.comparisons_done == 1
    assert loaded.question_id == 2


@pytest.mark.asyncio
async def test_undo_restores(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v2",
        prev_state_json="v1",
        comparisons_done=2,
        estimated_total=10,
        question_id=3,
    )
    undone = await repo.undo(session.id)
    assert undone is not None
    assert undone.state_json == "v1"
    assert undone.prev_state_json is None
    assert undone.comparisons_done == 1
    assert undone.question_id == 2


@pytest.mark.asyncio
async def test_undo_without_prev(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    undone = await repo.undo(session.id)
    assert undone is not None
    assert undone.state_json == "v1"


@pytest.mark.asyncio
async def test_finish_moves_to_results_and_deletes_session(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=5,
        estimated_total=10,
        question_id=4,
    )
    await repo.finish(
        session,
        result_json='{"terminal": {}}',
        comparisons_done=5,
        estimated_total=10,
    )
    assert await repo.load_by_id(session.id) is None
    assert await repo.load_active(1) is None
    assert await repo.latest_result(1) == '{"terminal": {}}'


@pytest.mark.asyncio
async def test_latest_result_returns_most_recent(repo: SessionsRepository) -> None:
    first = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=1,
        estimated_total=10,
    )
    await repo.finish(
        first,
        result_json='{"first": true}',
        comparisons_done=1,
        estimated_total=10,
    )

    second = await repo.create(
        1,
        state_json="v2",
        prev_state_json=None,
        comparisons_done=2,
        estimated_total=10,
    )
    await repo.finish(
        second,
        result_json='{"second": true}',
        comparisons_done=2,
        estimated_total=10,
    )

    assert await repo.latest_result(1) == '{"second": true}'


@pytest.mark.asyncio
async def test_delete(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.delete(session.id)
    assert await repo.load_active(1) is None


@pytest.mark.asyncio
async def test_update_last_question_message(repo: SessionsRepository) -> None:
    session = await repo.create(
        1,
        state_json="v1",
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=10,
    )
    await repo.update_last_question_message(session.id, chat_id=100, message_id=200)
    loaded = await repo.load_by_id(session.id)
    assert loaded is not None
    assert loaded.last_question_chat_id == 100
    assert loaded.last_question_message_id == 200
