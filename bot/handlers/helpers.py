from __future__ import annotations

from aiogram.types import Message

from bot.services import events
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.targets import MessageTarget


async def render_event(
    renderer: Renderer,
    event: events.SessionEvent,
    target: MessageTarget,
    service: SessionService,
    user_id: int,
) -> None:
    sent = await renderer.render(event, target)
    if isinstance(sent, Message):
        await service.record_last_question(
            user_id,
            chat_id=sent.chat.id,
            message_id=sent.message_id,
        )
