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
from bot.testflow import STAGE_LOWER, STAGE_THEMES, TestResult, TestState, TrackId
from bot.texts import (
    ALREADY_FINISHED,
    LOWER_PROMPT,
    NO_RESULT,
    QUESTION_PROMPT,
    RESUME_PROMPT,
    RESTART_CONFIRM,
    TEST_FINISHED,
    UNDO_UNAVAILABLE,
    WELCOME,
)
from bot.values import (
    CATEGORY_ORDER,
    Catalog,
    Theme,
    ValueItem,
    initial_estimated_total,
    load_catalog,
    theme_examples,
)

router = Router()

CATALOG: Catalog = load_catalog()
ESTIMATED_TOTAL = initial_estimated_total(CATALOG)

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
    return f"<code>[{''.join(chars)}]</code> {percent}%"


OPTION_EMOJI = ("1️⃣", "2️⃣", "3️⃣")


def _category_header(track: TrackId) -> str:
    category = CATALOG.categories[track.category]
    if track.stage == STAGE_THEMES:
        suffix = " · Сравнение тем"
    elif track.stage == STAGE_LOWER:
        suffix = " · Дополнительные ценности"
    else:
        suffix = ""
    return f"<b>{html.escape(category.name)}{suffix}</b>"


def _format_value_option(value: ValueItem) -> str:
    return f"<b>{html.escape(value.name)}</b>\n<i>{html.escape(value.description)}</i>"


def _format_theme_option(theme: Theme) -> str:
    examples = ", ".join(theme_examples(theme, CATALOG, 3))
    return (
        f"<b>{html.escape(theme.name)}</b>\n"
        f"<i>например: {html.escape(examples)}</i>"
    )


def _format_option_card(track: TrackId, key: str) -> str:
    if track.stage == STAGE_THEMES:
        return _format_theme_option(CATALOG.themes[key])
    return _format_value_option(CATALOG.values[key])


def _button_label(track: TrackId, key: str) -> str:
    if track.stage == STAGE_THEMES:
        return CATALOG.themes[key].name
    return CATALOG.values[key].name


def _question_prompt(track: TrackId) -> str:
    if track.stage == STAGE_LOWER:
        return LOWER_PROMPT
    return QUESTION_PROMPT


def format_question_text(
    track: TrackId,
    keys: tuple[str, ...],
    *,
    comparisons_done: int,
    estimated_total: int,
) -> str:
    next_question = comparisons_done + 1
    bar = progress_bar(comparisons_done, estimated_total)
    option_blocks = "\n\n".join(
        f"{OPTION_EMOJI[index]} {_format_option_card(track, key)}"
        for index, key in enumerate(keys)
    )
    return (
        f"{_category_header(track)}\n\n"
        f"<b>{_question_prompt(track)}</b>\n\n"
        f"{option_blocks}\n\n"
        f"<b>{next_question}/{estimated_total}</b> {bar}"
    )


def format_result_text(result: TestResult) -> str:
    lines = [f"<b>{TEST_FINISHED}</b>", ""]

    for category_key in CATEGORY_ORDER:
        category = CATALOG.categories[category_key]
        category_result = result.by_category[category_key]
        lines.append(f"<b>{html.escape(category.name)}</b>")

        if category_result.important:
            lines.append("")
            lines.append("<b>Важные (по убыванию значимости):</b>")
            for position, value_key in enumerate(category_result.important, start=1):
                value = CATALOG.values[value_key]
                lines.append(
                    f"{position}. <b>{html.escape(value.name)}</b>"
                    f" — <i>{html.escape(value.description)}</i>"
                )

        if category_result.also_important:
            lines.append("")
            lines.append("<b>Также важные (без определённого порядка):</b>")
            for value_key in category_result.also_important:
                value = CATALOG.values[value_key]
                lines.append(
                    f"• <b>{html.escape(value.name)}</b>"
                    f" — <i>{html.escape(value.description)}</i>"
                )

        if category_result.less_important:
            lines.append("")
            lines.append("<b>Менее важные:</b>")
            for value_key in category_result.less_important:
                value = CATALOG.values[value_key]
                lines.append(
                    f"• <b>{html.escape(value.name)}</b>"
                    f" — <i>{html.escape(value.description)}</i>"
                )

        lines.append("")

    return "\n".join(lines).rstrip()


def _parse_result_json(payload: str | None) -> TestResult:
    data = json.loads(payload or "{}")
    return TestResult.from_dict(data)


async def _create_new_session(user_id: int) -> db.Session:
    state = TestState.initial(CATALOG)
    estimated_total = state.estimated_total(CATALOG)
    await db.save_session(
        user_id,
        state_json=state.to_json(),
        prev_state_json=None,
        comparisons_done=0,
        estimated_total=estimated_total,
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
        text = format_result_text(_parse_result_json(session.result_json))
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    state = TestState.from_json(session.state_json)
    if state.is_done():
        result = state.result(CATALOG)
        result_json = json.dumps(result.to_dict(), ensure_ascii=False)
        await db.finish_session(
            user_id=session.user_id,
            state_json=state.to_json(),
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(CATALOG),
            result_json=result_json,
        )
        text = format_result_text(result)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    track = state.current_track()
    keys = state.current_keys()
    if track is None or keys is None:
        result = state.result(CATALOG)
        result_json = json.dumps(result.to_dict(), ensure_ascii=False)
        await db.finish_session(
            user_id=session.user_id,
            state_json=state.to_json(),
            comparisons_done=state.comparisons_done(),
            estimated_total=state.estimated_total(CATALOG),
            result_json=result_json,
        )
        text = format_result_text(result)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    estimated_total = state.estimated_total(CATALOG)
    text = format_question_text(
        track,
        keys,
        comparisons_done=state.comparisons_done(),
        estimated_total=estimated_total,
    )
    keyboard = question_keyboard([_button_label(track, key) for key in keys])
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
        await message.answer(ALREADY_FINISHED)
        return

    if session and not session.is_finished:
        state = TestState.from_json(session.state_json)
        await message.answer(
            RESUME_PROMPT.format(
                bar=progress_bar(
                    state.comparisons_done(),
                    state.estimated_total(CATALOG),
                ),
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
        try:
            await message.bot.delete_message(
                chat_id=session.last_question_chat_id,
                message_id=session.last_question_message_id,
            )
        except TelegramBadRequest:
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=session.last_question_chat_id,
                    message_id=session.last_question_message_id,
                    reply_markup=None,
                )
            except TelegramBadRequest:
                pass

    await _render_question(message, session, edit=False)


@router.message(Command("result"))
async def cmd_result(message: Message) -> None:
    session = await db.load_session(message.from_user.id)
    if session is None or not session.is_finished or not session.result_json:
        await message.answer(NO_RESULT)
        return
    await message.answer(format_result_text(_parse_result_json(session.result_json)))


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

    state = TestState.from_json(session.state_json)
    prev_state_json = session.state_json
    state.step(choice, CATALOG)
    comparisons_done = state.comparisons_done()
    estimated_total = state.estimated_total(CATALOG)

    if state.is_done():
        result = state.result(CATALOG)
        result_json = json.dumps(result.to_dict(), ensure_ascii=False)
        await db.finish_session(
            user_id=callback.from_user.id,
            state_json=state.to_json(),
            comparisons_done=comparisons_done,
            estimated_total=estimated_total,
            result_json=result_json,
        )
        await callback.answer()
        await callback.message.edit_text(format_result_text(result))
        return

    await db.save_session(
        callback.from_user.id,
        state_json=state.to_json(),
        prev_state_json=prev_state_json,
        comparisons_done=comparisons_done,
        estimated_total=estimated_total,
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
