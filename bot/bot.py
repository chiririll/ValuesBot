from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.config import require_bot_token
from bot.db import init_db
from bot.handlers import router

logging.basicConfig(level=logging.INFO)


BOT_COMMANDS = [
    BotCommand(command="start", description="Начать или продолжить тест"),
    BotCommand(command="undo", description="Отменить последний выбор"),
    BotCommand(command="restart", description="Начать тест заново"),
    BotCommand(command="result", description="Показать результат"),
]


async def run_bot() -> None:
    await init_db()

    bot = Bot(
        token=require_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(BOT_COMMANDS)

    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)
