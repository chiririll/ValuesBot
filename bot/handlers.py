from __future__ import annotations

import html
import json

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import db
from bot.keyboards import (
    question_keyboard,
    restart_confirm_keyboard,
    resume_keyboard,
    start_keyboard,
)
from bot.sort import MergeSortState
from bot.texts import (
    ALREADY_FINISHED,
    NO_RESULT,
    QUESTION_PROMPT,
    RESUME_PROMPT,
    RESTART_CONFIRM,
    TEST_FINISHED,
    UNDO_DONE,
    UNDO_UNAVAILABLE,
    WELCOME,
)
from bot.values import Value, estimate_comparisons, load_values

router = Router()

VALUES: list[Value] = load_values()
ESTIMATED_TOTAL = estimate_comparisons(len(VALUES))

PROGRESS_BAR_WIDTH = 15
BRAILLE_LEVELS = "\u2800\u2840\u2844\u2846\u2847\u28c7\u28e7\u28f7\u28ff"


def progress_bar(done: int, total: int, width: int = PROGRESS_BAR_WIDTH) -> str:
    total = max(total, 1)
    ratio = min(max(done / total, 0.0), 1.0)
    total_dots = width * 8
    filled_dots = int(round(ratio * total_dots))
    filled_dots = min(filled_dots, total_dots)

    chars = []
    for index in range(width):
        column_dots = max(0, min(8, filled_dots - index * 8))
        chars.append(BRAILLE_LEVELS[column_dots])

    percent = int(round(ratio * 100))
    return f"<code>{''.join(chars)}</code> {percent}%"


def _format_option(value: Value) -> str:
    return f"<b>{html.escape(value.name)}</b>\n<i>{html.escape(value.description)}</i>"


def format_question_text(
    left: Value,
    right: Value,
    *,
    comparisons_done: int,
    estimated_total: int,
) -> str:
    next_question = comparisons_done + 1
    bar = progress_bar(comparisons_done, estimated_total)
    return (
        f"Вопрос <b>{next_question}</b> из {estimated_total}\n"
        f"{bar}\n\n"
        f"    <b>{QUESTION_PROMPT}</b>\n\n"
        f"1️⃣ {_format_option(left)}\n\n"
        f"2️⃣ {_format_option(right)}"
    )


def format_result_text(ranking: list[int]) -> str:
    lines = [f"<b>{TEST_FINISHED}</b>", ""]
    for position, value_index in enumerate(ranking, start=1):
        value = VALUES[value_index]
        lines.append(
            f"{position}. <b>{html.escape(value.name)}</b>"
            f" — <i>{html.escape(value.description)}</i>"
        )
    return "\n".join(lines)


async def _create_new_session(user_id: int) -> db.Session:
    state = MergeSortState.initial(len(VALUES))
    state_json = state.to_json()
    await db.save_session(
        user_id,
        state_json=state_json,
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=ESTIMATED_TOTAL,
    )
    session = await db.load_session(user_id)
    assert session is not None
    return session


async def _render_question(
    message: Message,
    session: db.Session,
    *,
    edit: bool = False,
) -> None:
    if session.is_finished:
        ranking = json.loads(session.result_json or "[]")
        text = format_result_text(ranking)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    state = MergeSortState.from_json(session.state_json)
    pair = state.current_pair()
    if pair is None:
        ranking = state.result()
        await db.finish_session(
            user_id=session.user_id,
            ranking=ranking,
            state_json=state.to_json(),
            comparisons_done=session.comparisons_done,
            estimated_total=session.estimated_total,
        )
        text = format_result_text(ranking)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    left = VALUES[pair[0]]
    right = VALUES[pair[1]]
    text = format_question_text(
        left,
        right,
        comparisons_done=session.comparisons_done,
        estimated_total=session.estimated_total,
    )
    keyboard = question_keyboard(left, right)
    if edit:
        sent = await message.edit_text(text, reply_markup=keyboard)
    else:
        sent = await message.answer(text, reply_markup=keyboard)

    if isinstance(sent, Message):
        await db.update_last_question_message(
            session.user_id,
            chat_id=sent.chat.id,
            message_id=sent.message_id,
        )


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    session = await db.load_session(user_id)

    if session and session.is_finished:
        await message.answer(
            ALREADY_FINISHED
            + "\n\n"
            + format_result_text(json.loads(session.result_json or "[]")),
        )
        return

    if session and not session.is_finished:
        await message.answer(
            RESUME_PROMPT.format(
                bar=progress_bar(session.comparisons_done, session.estimated_total),
            ),
            reply_markup=resume_keyboard(),
        )
        return

    await message.answer(
        WELCOME.format(total=ESTIMATED_TOTAL),
        reply_markup=start_keyboard(),
    )


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    await message.answer(RESTART_CONFIRM, reply_markup=restart_confirm_keyboard())


@router.message(Command("undo"))
async def cmd_undo(message: Message) -> None:
    if message.from_user is None or message.bot is None:
        return

    session_before = await db.load_session(message.from_user.id)
    if (
        session_before is None
        or session_before.is_finished
        or not session_before.prev_state_json
    ):
        await message.answer(UNDO_UNAVAILABLE)
        return

    session = await db.undo_session(message.from_user.id)
    if session is None:
        await message.answer(UNDO_UNAVAILABLE)
        return

    if (
        session.last_question_chat_id is not None
        and session.last_question_message_id is not None
    ):
        state = MergeSortState.from_json(session.state_json)
        pair = state.current_pair()
        if pair is not None:
            left = VALUES[pair[0]]
            right = VALUES[pair[1]]
            text = format_question_text(
                left,
                right,
                comparisons_done=session.comparisons_done,
                estimated_total=session.estimated_total,
            )
            try:
                await message.bot.edit_message_text(
                    text=text,
                    chat_id=session.last_question_chat_id,
                    message_id=session.last_question_message_id,
                    reply_markup=question_keyboard(left, right),
                )
                return
            except TelegramBadRequest:
                pass

    await message.answer(UNDO_DONE)
    await _render_question(message, session, edit=False)


@router.message(Command("result"))
async def cmd_result(message: Message) -> None:
    session = await db.load_session(message.from_user.id)
    if session is None or not session.is_finished or not session.result_json:
        await message.answer(NO_RESULT)
        return
    await message.answer(format_result_text(json.loads(session.result_json)))


@router.callback_query(F.data == "start:new")
async def on_start_new(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return

    session = await _create_new_session(callback.from_user.id)
    await _render_question(callback.message, session, edit=True)


@router.callback_query(F.data == "start:continue")
async def on_start_continue(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return

    session = await db.load_session(callback.from_user.id)
    if session is None or session.is_finished:
        session = await _create_new_session(callback.from_user.id)
    await _render_question(callback.message, session, edit=True)


@router.callback_query(F.data.startswith("pick:"))
async def on_pick(callback: CallbackQuery) -> None:
    if callback.message is None or callback.from_user is None:
        return

    choice = int(callback.data.split(":", maxsplit=1)[1])
    session = await db.load_session(callback.from_user.id)
    if session is None or session.is_finished:
        await callback.answer("Сессия не найдена. Нажмите /start.", show_alert=True)
        return

    state = MergeSortState.from_json(session.state_json)
    prev_state_json = session.state_json
    state.step(choice)
    comparisons_done = session.comparisons_done + 1

    if state.is_done():
        ranking = state.result()
        await db.finish_session(
            user_id=callback.from_user.id,
            ranking=ranking,
            state_json=state.to_json(),
            comparisons_done=comparisons_done,
            estimated_total=session.estimated_total,
        )
        await callback.answer()
        await callback.message.edit_text(format_result_text(ranking))
        return

    await db.save_session(
        callback.from_user.id,
        state_json=state.to_json(),
        prev_state_json=prev_state_json,
        comparisons_done=comparisons_done,
        estimated_total=session.estimated_total,
    )
    await callback.answer()
    updated = await db.load_session(callback.from_user.id)
    assert updated is not None
    await _render_question(callback.message, updated, edit=True)


@router.callback_query(F.data == "restart:confirm")
async def on_restart_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.edit_text(
        RESTART_CONFIRM, reply_markup=restart_confirm_keyboard()
    )


@router.callback_query(F.data == "restart:yes")
async def on_restart_yes(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return

    await db.delete_session(callback.from_user.id)
    session = await _create_new_session(callback.from_user.id)
    await _render_question(callback.message, session, edit=True)


@router.callback_query(F.data == "restart:no")
async def on_restart_no(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is None or callback.from_user is None:
        return

    session = await db.load_session(callback.from_user.id)
    if session and not session.is_finished:
        await _render_question(callback.message, session, edit=True)
        return

    await callback.message.edit_text(
        WELCOME.format(total=ESTIMATED_TOTAL),
        reply_markup=start_keyboard(),
    )
