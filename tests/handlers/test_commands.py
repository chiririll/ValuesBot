from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message, User

from bot.handlers import commands
from bot.services import events


@pytest.fixture
def message() -> AsyncMock:
    mock = AsyncMock(spec=Message)
    mock.from_user = User(id=1, is_bot=False, first_name="Test")
    mock.answer = AsyncMock(return_value=MagicMock(chat=MagicMock(id=1), message_id=1))
    mock.bot = AsyncMock()
    return mock


@pytest.fixture
def service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def renderer() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_cmd_start_new_user(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.start_or_resume = AsyncMock(return_value=events.Welcome(estimated_total=50))
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[0].callback
        await handler(message)
        render.assert_awaited_once()
        service.start_or_resume.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_cmd_restart(message: AsyncMock, service: AsyncMock, renderer: AsyncMock) -> None:
    service.restart_confirm = MagicMock(return_value=events.RestartConfirm())
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[1].callback
        await handler(message)
        render.assert_awaited_once()


@pytest.mark.asyncio
async def test_cmd_undo_unavailable(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.load_session = AsyncMock(return_value=None)
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[2].callback
        await handler(message)
        render.assert_awaited_once()


@pytest.mark.asyncio
async def test_cmd_result(message: AsyncMock, service: AsyncMock, renderer: AsyncMock) -> None:
    service.show_result = AsyncMock(return_value=events.NoResult())
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[3].callback
        await handler(message)
        service.show_result.assert_awaited_once_with(1)
        render.assert_awaited_once()
