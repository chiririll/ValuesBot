from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers.helpers import render_event
from bot.services import events
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.targets import AnswerTarget

logger = logging.getLogger(__name__)


def build_router(service: SessionService, renderer: Renderer) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        if message.from_user is None:
            return
        event = await service.start_or_resume(message.from_user.id)
        await render_event(renderer, event, AnswerTarget(message), service, message.from_user.id)

    @router.message(Command("restart"))
    async def cmd_restart(message: Message) -> None:
        if message.from_user is None:
            return
        event = service.restart_confirm()
        await render_event(renderer, event, AnswerTarget(message), service, message.from_user.id)

    @router.message(Command("undo"))
    async def cmd_undo(message: Message) -> None:
        if message.from_user is None or message.bot is None:
            return

        session_before = await service.load_session(message.from_user.id)
        if (
            session_before is None
            or session_before.is_finished
            or not session_before.prev_state_json
        ):
            await render_event(
                renderer,
                events.UndoUnavailable(),
                AnswerTarget(message),
                service,
                message.from_user.id,
            )
            return

        if (
            session_before.last_question_chat_id is not None
            and session_before.last_question_message_id is not None
        ):
            try:
                await message.bot.delete_message(
                    chat_id=session_before.last_question_chat_id,
                    message_id=session_before.last_question_message_id,
                )
            except TelegramBadRequest:
                with suppress(TelegramBadRequest):  # pragma: no cover
                    await message.bot.edit_message_reply_markup(
                        chat_id=session_before.last_question_chat_id,
                        message_id=session_before.last_question_message_id,
                        reply_markup=None,
                    )

        event = await service.undo(message.from_user.id)
        await render_event(renderer, event, AnswerTarget(message), service, message.from_user.id)

    @router.message(Command("result"))
    async def cmd_result(message: Message) -> None:
        if message.from_user is None:
            return
        event = await service.show_result(message.from_user.id)
        await render_event(renderer, event, AnswerTarget(message), service, message.from_user.id)

    return router
