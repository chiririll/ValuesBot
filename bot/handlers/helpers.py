from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from bot.db.sessions_repo import Session
from bot.services import events
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.targets import MessageTarget


def session_id_from_event(event: events.SessionEvent) -> int | None:
    match event:
        case events.Question(session_id=session_id):
            return session_id
        case events.Resume(session_id=session_id):
            return session_id
        case events.RestartConfirm(session_id=session_id):
            return session_id
    return None


async def render_event(
    renderer: Renderer,
    event: events.SessionEvent,
    target: MessageTarget,
    service: SessionService,
    user_id: int,
) -> None:
    sent = await renderer.render(event, target)
    session_id = session_id_from_event(event)
    if isinstance(sent, Message) and session_id is not None:
        await service.record_last_question(
            session_id,
            chat_id=sent.chat.id,
            message_id=sent.message_id,
        )


async def clear_last_question_message(bot: Bot, session: Session) -> None:
    if session.last_question_chat_id is None or session.last_question_message_id is None:
        return
    try:
        await bot.delete_message(
            chat_id=session.last_question_chat_id,
            message_id=session.last_question_message_id,
        )
    except TelegramBadRequest:
        with suppress(TelegramBadRequest):  # pragma: no cover
            await bot.edit_message_reply_markup(
                chat_id=session.last_question_chat_id,
                message_id=session.last_question_message_id,
                reply_markup=None,
            )
