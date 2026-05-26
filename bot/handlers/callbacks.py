from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.helpers import render_event
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.targets import EditMessageTarget
from bot.views.texts import SESSION_NOT_FOUND_ALERT

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

        choice = int(callback.data.split(":", maxsplit=1)[1])
        try:
            event = await service.advance(callback.from_user.id, choice)
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

    @router.callback_query(F.data == "restart:confirm")
    async def on_restart_confirm(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None:
            return
        event = service.restart_confirm()
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data == "restart:yes")
    async def on_restart_yes(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None:
            return
        event = await service.restart(callback.from_user.id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    @router.callback_query(F.data == "restart:no")
    async def on_restart_no(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None:
            return
        event = await service.start_or_resume(callback.from_user.id)
        await render_event(
            renderer,
            event,
            EditMessageTarget(callback),
            service,
            callback.from_user.id,
        )

    return router
