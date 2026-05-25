from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.values import Value


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start:new")],
        ]
    )


def resume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Продолжить", callback_data="start:continue")],
            [InlineKeyboardButton(text="Начать заново", callback_data="restart:confirm")],
        ]
    )


def question_keyboard(left: Value, right: Value) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=left.name, callback_data="pick:1"),
                InlineKeyboardButton(text=right.name, callback_data="pick:2"),
            ]
        ]
    )


def restart_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, начать заново", callback_data="restart:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="restart:no"),
            ]
        ]
    )
