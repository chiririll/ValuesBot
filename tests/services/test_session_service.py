from __future__ import annotations

import asyncio
import json

import pytest

from bot.core.testflow import TestState
from bot.core.values import Catalog
from bot.services import events
from bot.services.errors import StaleCallbackError
from bot.services.session_service import SessionService


@pytest.mark.asyncio
async def test_start_or_resume_new(service: SessionService) -> None:
    event = await service.start_or_resume(1)
    assert isinstance(event, events.Welcome)


@pytest.mark.asyncio
async def test_start_or_resume_in_progress(service: SessionService) -> None:
    await service.create_new(1)
    event = await service.start_or_resume(1)
    assert isinstance(event, events.Resume)
    assert event.session_id > 0


@pytest.mark.asyncio
async def test_start_or_resume_finished(service: SessionService, catalog: Catalog) -> None:
    created = await service.create_new(1)
    assert isinstance(created, events.Question)
    state = TestState.initial(catalog)
    while not state.is_done():
        keys = state.current_keys()
        if keys is None:
            break
        state.step(1, catalog)
    result_json = json.dumps(state.result(catalog).to_dict(), ensure_ascii=False)
    session = await service.load_session(1)
    assert session is not None
    await service._repo.finish(
        session,
        result_json=result_json,
        comparisons_done=state.comparisons_done(),
        estimated_total=state.estimated_total(catalog),
    )
    event = await service.start_or_resume(1)
    assert isinstance(event, events.AlreadyFinished)


@pytest.mark.asyncio
async def test_create_new_returns_question(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)
    assert event.track.stage == "themes"
    assert event.question_id == 1


@pytest.mark.asyncio
async def test_advance_to_finish(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)
    safety = 500
    while safety > 0:
        event = await service.advance(1, event.session_id, event.question_id, 1)
        if isinstance(event, events.Finished):
            break
        assert isinstance(event, events.Question)
        safety -= 1
    assert isinstance(event, events.Finished)
    assert await service.load_session(1) is None


@pytest.mark.asyncio
async def test_advance_rejects_stale_question_id(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)
    with pytest.raises(StaleCallbackError):
        await service.advance(1, event.session_id, event.question_id + 1, 1)


@pytest.mark.asyncio
async def test_advance_rejects_stale_session_id(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)
    with pytest.raises(StaleCallbackError):
        await service.advance(1, event.session_id + 999, event.question_id, 1)


@pytest.mark.asyncio
async def test_undo_after_advance(service: SessionService) -> None:
    first = await service.create_new(1)
    assert isinstance(first, events.Question)
    second = await service.advance(1, first.session_id, first.question_id, 1)
    assert isinstance(second, events.Question)
    undone = await service.undo(1)
    assert isinstance(undone, events.Question)
    assert undone.question_id == first.question_id


@pytest.mark.asyncio
async def test_undo_unavailable(service: SessionService) -> None:
    event = await service.undo(99)
    assert isinstance(event, events.UndoUnavailable)


@pytest.mark.asyncio
async def test_show_result_from_results_table(service: SessionService, catalog: Catalog) -> None:
    created = await service.create_new(1)
    assert isinstance(created, events.Question)
    state = TestState.initial(catalog)
    while not state.is_done():
        keys = state.current_keys()
        if keys is None:
            break
        state.step(1, catalog)
    result_json = json.dumps(state.result(catalog).to_dict(), ensure_ascii=False)
    session = await service.load_session(1)
    assert session is not None
    await service._repo.finish(
        session,
        result_json=result_json,
        comparisons_done=state.comparisons_done(),
        estimated_total=state.estimated_total(catalog),
    )
    event = await service.show_result(1)
    assert isinstance(event, events.Finished)


@pytest.mark.asyncio
async def test_record_last_question(service: SessionService, repo) -> None:
    created = await service.create_new(1)
    assert isinstance(created, events.Question)
    await service.record_last_question(
        created.session_id,
        chat_id=10,
        message_id=20,
    )
    session = await repo.load_by_id(created.session_id)
    assert session is not None
    assert session.last_question_chat_id == 10


@pytest.mark.asyncio
async def test_concurrent_advance_same_user(service: SessionService) -> None:
    event = await service.create_new(1)
    assert isinstance(event, events.Question)

    async def advance_once() -> events.SessionEvent:
        return await service.advance(1, event.session_id, event.question_id, 1)

    results = await asyncio.gather(advance_once(), advance_once(), return_exceptions=True)
    successes = [r for r in results if isinstance(r, (events.Question, events.Finished))]
    stale = [r for r in results if isinstance(r, StaleCallbackError)]
    assert len(successes) == 1
    assert len(stale) == 1
    session = await service.load_session(1)
    assert session is not None
    assert session.comparisons_done == 1


@pytest.mark.asyncio
async def test_concurrent_advance_different_users(service: SessionService) -> None:
    first = await service.create_new(1)
    second = await service.create_new(2)
    assert isinstance(first, events.Question)
    assert isinstance(second, events.Question)

    r1, r2 = await asyncio.gather(
        service.advance(1, first.session_id, first.question_id, 1),
        service.advance(2, second.session_id, second.question_id, 1),
    )
    assert isinstance(r1, events.Question)
    assert isinstance(r2, events.Question)
