from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.views.texts import (
    BTN_CONTINUE,
    BTN_RESTART,
    BTN_RESTART_CONFIRM_NO,
    BTN_RESTART_CONFIRM_YES,
    BTN_START,
)


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_START, callback_data="start:new")],
        ]
    )


def resume_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONTINUE, callback_data="start:continue")],
            [InlineKeyboardButton(text=BTN_RESTART, callback_data="restart:confirm")],
        ]
    )


def question_keyboard(labels: list[str]) -> InlineKeyboardMarkup:
    if not 2 <= len(labels) <= 3:
        raise ValueError("question_keyboard expects 2 or 3 labels")

    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"pick:{index + 1}")
        for index, label in enumerate(labels)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def restart_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_RESTART_CONFIRM_YES, callback_data="restart:yes"
                ),
                InlineKeyboardButton(
                    text=BTN_RESTART_CONFIRM_NO, callback_data="restart:no"
                ),
            ]
        ]
    )
