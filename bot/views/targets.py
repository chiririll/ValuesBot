from __future__ import annotations

from typing import Protocol

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


class MessageTarget(Protocol):
    async def send(
        self,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> Message | bool: ...


class AnswerTarget:
    def __init__(self, message: Message) -> None:
        self._message = message

    async def send(
        self,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> Message:
        return await self._message.answer(text, reply_markup=keyboard)


class EditMessageTarget:
    def __init__(self, callback: CallbackQuery) -> None:
        self._callback = callback

    async def send(
        self,
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        message = self._callback.message
        if message is None or not isinstance(message, Message):
            raise RuntimeError("Callback has no editable message")
        return await message.edit_text(text, reply_markup=keyboard)
