from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.core.stages import STAGE_LOWER, STAGE_THEMES, TrackId
from bot.core.testflow import CategoryResult, TestResult
from bot.core.values import Catalog
from bot.services import events
from bot.views.renderer import Renderer
from bot.views.texts import (
    ALREADY_FINISHED,
    LOWER_PROMPT,
    NO_RESULT,
    RESTART_CONFIRM,
    UNDO_UNAVAILABLE,
    WELCOME,
)


@pytest.fixture
def renderer(catalog: Catalog) -> Renderer:
    return Renderer(catalog)


@pytest.fixture
def target() -> AsyncMock:
    mock = AsyncMock()
    mock.send = AsyncMock(return_value=MagicMock(chat=MagicMock(id=1), message_id=1))
    return mock


@pytest.mark.asyncio
async def test_render_welcome(renderer: Renderer, target: AsyncMock) -> None:
    await renderer.render(events.Welcome(estimated_total=50), target)
    target.send.assert_awaited_once()
    assert "50" in target.send.await_args.args[0]
    assert WELCOME.split("{")[0] in target.send.await_args.args[0]


@pytest.mark.asyncio
async def test_render_resume(renderer: Renderer, target: AsyncMock) -> None:
    await renderer.render(events.Resume(comparisons_done=5, estimated_total=50), target)
    assert "50%" in target.send.await_args.args[0] or "%" in target.send.await_args.args[0]


@pytest.mark.asyncio
async def test_render_question_themes(renderer: Renderer, target: AsyncMock) -> None:
    event = events.Question(
        track=TrackId("terminal", STAGE_THEMES),
        keys=("Тема A", "Тема B"),
        comparisons_done=0,
        estimated_total=10,
    )
    await renderer.render(event, target)
    keyboard = target.send.await_args.kwargs.get("reply_markup") or target.send.await_args.args[1]
    assert keyboard is not None
    assert len(keyboard.inline_keyboard[0]) == 2


@pytest.mark.asyncio
async def test_render_question_lower(renderer: Renderer, target: AsyncMock) -> None:
    event = events.Question(
        track=TrackId("terminal", STAGE_LOWER),
        keys=("A1", "A2", "A3"),
        comparisons_done=0,
        estimated_total=5,
    )
    await renderer.render(event, target)
    assert LOWER_PROMPT in target.send.await_args.args[0]
    keyboard = target.send.await_args.kwargs.get("reply_markup") or target.send.await_args.args[1]
    assert len(keyboard.inline_keyboard[0]) == 3


@pytest.mark.asyncio
async def test_render_finished(renderer: Renderer, target: AsyncMock, catalog: Catalog) -> None:
    result = TestResult(
        by_category={
            "terminal": CategoryResult([], [], []),
            "instrumental": CategoryResult([], [], []),
        }
    )
    await renderer.render(events.Finished(result=result), target)
    assert target.send.await_args.kwargs.get("reply_markup") is None or (
        len(target.send.await_args.args) > 1 and target.send.await_args.args[1] is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event", "snippet"),
    [
        (events.AlreadyFinished(), ALREADY_FINISHED),
        (events.NoResult(), NO_RESULT),
        (events.UndoUnavailable(), UNDO_UNAVAILABLE),
        (events.RestartConfirm(), RESTART_CONFIRM),
    ],
)
async def test_render_simple_messages(
    renderer: Renderer,
    target: AsyncMock,
    event: events.SessionEvent,
    snippet: str,
) -> None:
    await renderer.render(event, target)
    assert snippet in target.send.await_args.args[0]
