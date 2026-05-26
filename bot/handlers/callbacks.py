from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.helpers import render_event
from bot.services.errors import StaleCallbackError
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.targets import EditMessageTarget
from bot.views.texts import SESSION_NOT_FOUND_ALERT, STALE_CALLBACK_ALERT

logger = logging.getLogger(__name__)


def build_router(service: SessionService, renderer: Renderer) -> Router:
    router = Router()

    @router.callback_query(F.data == "start:new")
    async def on_start_new(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None:
            return
        event = await service.create_new(callback.from_user.id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data == "start:continue")
    async def on_start_continue(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None:
            return
        event = await service.continue_session(callback.from_user.id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data.startswith("pick:"))
    async def on_pick(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.data is None:
            return

        parts = callback.data.split(":")
        if len(parts) != 4:
            await callback.answer(STALE_CALLBACK_ALERT, show_alert=True)
            return

        session_id = int(parts[1])
        question_id = int(parts[2])
        choice = int(parts[3])
        try:
            event = await service.advance(
                callback.from_user.id,
                session_id,
                question_id,
                choice,
            )
        except StaleCallbackError:
            await callback.answer(STALE_CALLBACK_ALERT, show_alert=True)
            return
        except RuntimeError:
            await callback.answer(SESSION_NOT_FOUND_ALERT, show_alert=True)
            return

        await callback.answer()
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data.startswith("restart:confirm:"))
    async def on_restart_confirm(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None or callback.data is None:
            return
        session_id = int(callback.data.split(":", maxsplit=2)[2])
        event = service.restart_confirm(session_id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data.startswith("restart:yes:"))
    async def on_restart_yes(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None or callback.data is None:
            return
        session_id = int(callback.data.split(":", maxsplit=2)[2])
        try:
            event = await service.restart(callback.from_user.id, session_id)
        except StaleCallbackError:
            await callback.answer(STALE_CALLBACK_ALERT, show_alert=True)
            return
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data.startswith("restart:no:"))
    async def on_restart_no(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None or callback.data is None:
            return
        session_id = int(callback.data.split(":", maxsplit=2)[2])
        session = await service.load_session(callback.from_user.id)
        if session is None or session.id != session_id:
            await callback.answer(STALE_CALLBACK_ALERT, show_alert=True)
            return
        event = await service.continue_session(callback.from_user.id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    return router
