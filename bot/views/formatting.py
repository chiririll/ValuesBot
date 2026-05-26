from __future__ import annotations

import html

from bot.core.stages import STAGE_LOWER, STAGE_THEMES, TrackId
from bot.core.testflow import TestResult
from bot.core.values import CATEGORY_ORDER, Catalog, Theme, ValueItem, theme_examples
from bot.views.texts import LOWER_PROMPT, QUESTION_PROMPT, TEST_FINISHED

PROGRESS_BAR_WIDTH = 15
BRAILLE_LEVELS = "\u2800\u2840\u2844\u2846\u2847\u28c7\u28e7\u28f7\u28ff"
OPTION_EMOJI = ("1️⃣", "2️⃣", "3️⃣")


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


def _category_header(catalog: Catalog, track: TrackId) -> str:
    category = catalog.categories[track.category]
    if track.stage == STAGE_THEMES:
        suffix = " · Сравнение тем"
    elif track.stage == STAGE_LOWER:
        suffix = " · Дополнительные ценности"
    else:
        suffix = ""
    return f"<b>{html.escape(category.name)}{suffix}</b>"


def _format_value_option(value: ValueItem) -> str:
    return f"<b>{html.escape(value.name)}</b>\n<i>{html.escape(value.description)}</i>"


def _format_theme_option(catalog: Catalog, theme: Theme) -> str:
    examples = ", ".join(theme_examples(theme, catalog, 3))
    return f"<b>{html.escape(theme.name)}</b>\n<i>например: {html.escape(examples)}</i>"


def _format_option_card(catalog: Catalog, track: TrackId, key: str) -> str:
    if track.stage == STAGE_THEMES:
        return _format_theme_option(catalog, catalog.themes[key])
    return _format_value_option(catalog.values[key])


def button_label(catalog: Catalog, track: TrackId, key: str) -> str:
    if track.stage == STAGE_THEMES:
        return catalog.themes[key].name
    return catalog.values[key].name


def _question_prompt(track: TrackId) -> str:
    if track.stage == STAGE_LOWER:
        return LOWER_PROMPT
    return QUESTION_PROMPT


def format_question_text(
    catalog: Catalog,
    track: TrackId,
    keys: tuple[str, ...],
    *,
    comparisons_done: int,
    estimated_total: int,
) -> str:
    next_question = comparisons_done + 1
    bar = progress_bar(comparisons_done, estimated_total)
    option_blocks = "\n\n".join(
        f"{OPTION_EMOJI[index]} {_format_option_card(catalog, track, key)}"
        for index, key in enumerate(keys)
    )
    return (
        f"{_category_header(catalog, track)}\n\n"
        f"<b>{_question_prompt(track)}</b>\n\n"
        f"{option_blocks}\n\n"
        f"<b>{next_question}/{estimated_total}</b> {bar}"
    )


def format_result_text(catalog: Catalog, result: TestResult) -> str:
    lines = [f"<b>{TEST_FINISHED}</b>", ""]

    for category_key in CATEGORY_ORDER:
        category = catalog.categories[category_key]
        category_result = result.by_category[category_key]
        lines.append(f"<b>{html.escape(category.name)}</b>")

        if category_result.important:
            lines.append("")
            lines.append("<b>Важные (по убыванию значимости):</b>")
            for position, value_key in enumerate(category_result.important, start=1):
                value = catalog.values[value_key]
                lines.append(
                    f"{position}. <b>{html.escape(value.name)}</b>"
                    f" — <i>{html.escape(value.description)}</i>"
                )

        if category_result.also_important:
            lines.append("")
            lines.append("<b>Также важные (без определённого порядка):</b>")
            for value_key in category_result.also_important:
                value = catalog.values[value_key]
                lines.append(
                    f"• <b>{html.escape(value.name)}</b> — <i>{html.escape(value.description)}</i>"
                )

        if category_result.less_important:
            lines.append("")
            lines.append("<b>Менее важные:</b>")
            for value_key in category_result.less_important:
                value = catalog.values[value_key]
                lines.append(
                    f"• <b>{html.escape(value.name)}</b> — <i>{html.escape(value.description)}</i>"
                )

        lines.append("")

    return "\n".join(lines).rstrip()
