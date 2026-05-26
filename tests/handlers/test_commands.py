from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, User

from bot.db.sessions_repo import Session
from bot.handlers import commands
from bot.services import events


def _session_with_last_question(
    chat_id: int | None = 100,
    message_id: int | None = 200,
    *,
    prev_state_json: str | None = '{"old": true}',
) -> Session:
    return Session(
        id=10,
        user_id=1,
        state_json='{"current": true}',
        prev_state_json=prev_state_json,
        comparisons_done=1,
        estimated_total=10,
        question_id=2,
        last_question_chat_id=chat_id,
        last_question_message_id=message_id,
    )


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
async def test_cmd_restart_no_session(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.load_session = AsyncMock(return_value=None)
    router = commands.build_router(service, renderer)

    handler = router.message.handlers[1].callback
    await handler(message)
    message.answer.assert_awaited_once()
    message.bot.delete_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_cmd_restart_clears_previous_question(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.load_session = AsyncMock(return_value=_session_with_last_question())
    service.restart_confirm = MagicMock(return_value=events.RestartConfirm(session_id=10))
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[1].callback
        await handler(message)
        message.bot.delete_message.assert_awaited_once_with(chat_id=100, message_id=200)
        service.restart_confirm.assert_called_once_with(10)
        render.assert_awaited_once()


@pytest.mark.asyncio
async def test_cmd_restart_falls_back_to_removing_keyboard(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.load_session = AsyncMock(return_value=_session_with_last_question())
    service.restart_confirm = MagicMock(return_value=events.RestartConfirm(session_id=10))
    message.bot.delete_message = AsyncMock(
        side_effect=TelegramBadRequest(method=MagicMock(), message="too old")
    )
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock):
        handler = router.message.handlers[1].callback
        await handler(message)
        message.bot.edit_message_reply_markup.assert_awaited_once_with(
            chat_id=100, message_id=200, reply_markup=None
        )


@pytest.mark.asyncio
async def test_cmd_restart_skips_cleanup_when_no_last_question(
    message: AsyncMock, service: AsyncMock, renderer: AsyncMock
) -> None:
    service.load_session = AsyncMock(
        return_value=_session_with_last_question(chat_id=None, message_id=None)
    )
    service.restart_confirm = MagicMock(return_value=events.RestartConfirm(session_id=10))
    router = commands.build_router(service, renderer)

    with patch("bot.handlers.commands.render_event", new_callable=AsyncMock) as render:
        handler = router.message.handlers[1].callback
        await handler(message)
        message.bot.delete_message.assert_not_awaited()
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
