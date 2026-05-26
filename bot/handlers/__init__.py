from __future__ import annotations

from aiogram import Router

from bot.handlers import callbacks, commands
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer


def build_router(service: SessionService, renderer: Renderer) -> Router:
    router = Router()
    router.include_router(commands.build_router(service, renderer))
    router.include_router(callbacks.build_router(service, renderer))
    return router
