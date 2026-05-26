from __future__ import annotations

import asyncio

import pytest

from bot.core.testflow import TestState
from bot.core.values import Catalog
from bot.services import events
from bot.services.session_service import SessionService


@pytest.mark.asyncio
async def test_start_or_resume_new(service: SessionService) -> None:
    event = await service.start_or_resume(1)
    assert isinstance(event, events.Welcome)


@pytest.mark.asyncio
async def test_start_or_resume_in_progress(service: SessionService, catalog: Catalog) -> None:
    await service.create_new(1)
    event = await service.start_or_resume(1)
    assert isinstance(event, events.Resume)


@pytest.mark.asyncio
async def test_start_or_resume_finished(service: SessionService, catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    while not state.is_done():
        keys = state.current_keys()
        if keys is None:
            break
        state.step(1, catalog)
    result_json = __import__("json").dumps(state.result(catalog).to_dict(), ensure_ascii=False)
    await service._repo.finish(
        1,
        state_json=state.to_json(),
        comparisons_done=state.comparisons_done(),
        estimated_total=state.estimated_total(catalog),
        result_json=result_json,
    )
    event = await service.start_or_resume(1)
    assert isinstance(event, events.AlreadyFinished)


@pytest.mark.asyncio
async def test_create_new_returns_question(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)
    assert event.track.stage == "themes"


@pytest.mark.asyncio
async def test_advance_to_finish(service: SessionService, catalog: Catalog) -> None:
    await service.create_new(1)
    safety = 500
    while safety > 0:
        event = await service.advance(1, 1)
        if isinstance(event, events.Finished):
            break
        assert isinstance(event, events.Question)
        safety -= 1
    assert isinstance(event, events.Finished)


@pytest.mark.asyncio
async def test_undo_after_advance(service: SessionService) -> None:
    await service.create_new(1)
    first = await service.advance(1, 1)
    assert isinstance(first, events.Question)
    undone = await service.undo(1)
    assert isinstance(undone, events.Question)


@pytest.mark.asyncio
async def test_undo_unavailable(service: SessionService) -> None:
    event = await service.undo(99)
    assert isinstance(event, events.UndoUnavailable)


@pytest.mark.asyncio
async def test_record_last_question(service: SessionService, repo) -> None:
    await service.create_new(1)
    await service.record_last_question(1, chat_id=10, message_id=20)
    session = await repo.load(1)
    assert session is not None
    assert session.last_question_chat_id == 10


@pytest.mark.asyncio
async def test_concurrent_advance_same_user(service: SessionService) -> None:
    await service.create_new(1)

    async def advance_once() -> events.SessionEvent:
        return await service.advance(1, 1)

    results = await asyncio.gather(advance_once(), advance_once())
    assert all(isinstance(r, (events.Question, events.Finished)) for r in results)
    session = await service.load_session(1)
    assert session is not None
    assert session.comparisons_done == 2


@pytest.mark.asyncio
async def test_concurrent_advance_different_users(service: SessionService) -> None:
    await service.create_new(1)
    await service.create_new(2)

    r1, r2 = await asyncio.gather(
        service.advance(1, 1),
        service.advance(2, 1),
    )
    assert isinstance(r1, events.Question)
    assert isinstance(r2, events.Question)
