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


def question_keyboard(left: Value, right: Value, *, can_undo: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=f"1. {left.name}", callback_data="pick:1"),
            InlineKeyboardButton(text=f"2. {right.name}", callback_data="pick:2"),
        ]
    ]
    if can_undo:
        rows.append(
            [InlineKeyboardButton(text="◀ Отменить последний выбор", callback_data="undo")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def restart_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, начать заново", callback_data="restart:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="restart:no"),
            ]
        ]
    )
