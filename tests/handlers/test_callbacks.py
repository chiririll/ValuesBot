from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Message, User

from bot.handlers import callbacks
from bot.services import events


@pytest.fixture
def callback() -> AsyncMock:
    mock = AsyncMock(spec=CallbackQuery)
    mock.from_user = User(id=1, is_bot=False, first_name="Test")
    mock.data = "pick:1"
    mock.message = AsyncMock(spec=Message)
    mock.message.edit_text = AsyncMock(return_value=MagicMock(chat=MagicMock(id=1), message_id=1))
    mock.answer = AsyncMock()
    return mock


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def renderer() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_on_start_new(callback: AsyncMock, service: AsyncMock, renderer: AsyncMock) -> None:
    service.create_new = AsyncMock(
        return_value=events.Question(
            track=MagicMock(),
            keys=("A", "B"),
            comparisons_done=0,
            estimated_total=10,
        )
    )
    router = callbacks.build_router(service, renderer)

    with patch("bot.handlers.callbacks.render_event", new_callable=AsyncMock) as render:
        handler = router.callback_query.handlers[0].callback
        await handler(callback)
        service.create_new.assert_awaited_once_with(1)
        render.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_pick(callback: AsyncMock, service: AsyncMock, renderer: AsyncMock) -> None:
    service.advance = AsyncMock(
        return_value=events.Question(
            track=MagicMock(),
            keys=("A", "B"),
            comparisons_done=1,
            estimated_total=10,
        )
    )
    router = callbacks.build_router(service, renderer)

    with patch("bot.handlers.callbacks.render_event", new_callable=AsyncMock) as render:
        handler = router.callback_query.handlers[2].callback
        await handler(callback)
        service.advance.assert_awaited_once_with(1, 1)
        render.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_pick_no_session(
    callback: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.advance = AsyncMock(side_effect=RuntimeError("not found"))
    router = callbacks.build_router(service, renderer)

    handler = router.callback_query.handlers[2].callback
    await handler(callback)
    callback.answer.assert_awaited()


@pytest.mark.asyncio
async def test_on_restart_yes(callback: AsyncMock, service: AsyncMock, renderer: AsyncMock) -> None:
    service.restart = AsyncMock(
        return_value=events.Question(
            track=MagicMock(),
            keys=("A", "B"),
            comparisons_done=0,
            estimated_total=10,
        )
    )
    router = callbacks.build_router(service, renderer)

    with patch("bot.handlers.callbacks.render_event", new_callable=AsyncMock) as render:
        handler = router.callback_query.handlers[4].callback
        await handler(callback)
        service.restart.assert_awaited_once_with(1)
        render.assert_awaited_once()
