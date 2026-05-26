from __future__ import annotations

from bot.views import keyboards


def test_question_keyboard_includes_session_and_question_ids() -> None:
    keyboard = keyboards.question_keyboard(
        ["A", "B"],
        session_id=42,
        question_id=7,
    )
    assert keyboard.inline_keyboard[0][0].callback_data == "pick:42:7:1"
    assert keyboard.inline_keyboard[0][1].callback_data == "pick:42:7:2"


def test_restart_confirm_keyboard_includes_session_id() -> None:
    keyboard = keyboards.restart_confirm_keyboard(99)
    yes, no = keyboard.inline_keyboard[0]
    assert yes.callback_data == "restart:yes:99"
    assert no.callback_data == "restart:no:99"
