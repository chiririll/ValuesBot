from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import require_bot_token
from bot.db import init_db
from bot.handlers import router

logging.basicConfig(level=logging.INFO)


async def run_bot() -> None:
    await init_db()

    bot = Bot(
        token=require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)
