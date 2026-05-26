from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import load_settings
from bot.core.values import load_catalog
from bot.db.sessions_repo import SessionsRepository
from bot.handlers import build_router
from bot.services.session_service import SessionService
from bot.views.renderer import Renderer
from bot.views.texts import BOT_COMMANDS

logging.basicConfig(level=logging.INFO)

_AIOGRAM_COMMANDS = [
    BotCommand(command=command, description=description)
    for command, description in BOT_COMMANDS
]


async def run_bot() -> None:
    settings = load_settings()
    catalog = load_catalog(settings.values_path)
    repo = SessionsRepository(settings.db_path)
    await repo.init()
    service = SessionService(repo, catalog)
    renderer = Renderer(catalog)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(_AIOGRAM_COMMANDS)

    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(service, renderer))

    try:
        await dispatcher.start_polling(bot)
    finally:
        await repo.close()
