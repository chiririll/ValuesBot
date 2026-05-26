from __future__ import annotations

from bot.core.stages import STAGE_LOWER, STAGE_THEMES, STAGE_VALUES, TrackId
from bot.core.testflow import CategoryResult, TestResult
from bot.core.values import Catalog
from bot.views.formatting import format_question_text, format_result_text, progress_bar


def test_progress_bar_empty(catalog: Catalog) -> None:
    bar = progress_bar(0, 100)
    assert "0%" in bar
    assert "\u2800" in bar


def test_progress_bar_full() -> None:
    bar = progress_bar(100, 100)
    assert "100%" in bar
    assert "\u28ff" in bar


def test_progress_bar_half() -> None:
    bar = progress_bar(50, 100)
    assert "50%" in bar


def test_format_question_themes(catalog: Catalog) -> None:
    track = TrackId(category="terminal", stage=STAGE_THEMES)
    text = format_question_text(
        catalog,
        track,
        ("Тема A", "Тема B"),
        comparisons_done=0,
        estimated_total=10,
    )
    assert "Терминальные" in text
    assert "Сравнение тем" in text


def test_format_question_values(catalog: Catalog) -> None:
    track = TrackId(category="terminal", stage=STAGE_VALUES)
    text = format_question_text(
        catalog,
        track,
        ("A1", "A2"),
        comparisons_done=5,
        estimated_total=20,
    )
    assert "Что для вас важнее" in text


def test_format_question_lower(catalog: Catalog) -> None:
    track = TrackId(category="terminal", stage=STAGE_LOWER)
    text = format_question_text(
        catalog,
        track,
        ("A1", "A2", "A3"),
        comparisons_done=1,
        estimated_total=5,
    )
    assert "наименее важна" in text


def test_format_result_all_sections(catalog: Catalog) -> None:
    result = TestResult(
        by_category={
            "terminal": CategoryResult(
                important=["A1"],
                also_important=["B1"],
                less_important=["C1"],
            ),
            "instrumental": CategoryResult(
                important=["X1"],
                also_important=[],
                less_important=[],
            ),
        }
    )
    text = format_result_text(catalog, result)
    assert "Важные" in text
    assert "Также важные" in text
    assert "Менее важные" in text


def test_html_escape_in_name(catalog: Catalog) -> None:
    catalog.values["A1"]  # noqa: B018 — ensure exists
    track = TrackId(category="terminal", stage=STAGE_VALUES)
    text = format_question_text(
        catalog,
        track,
        ("A1", "A2"),
        comparisons_done=0,
        estimated_total=5,
    )
    assert "<script>" not in text
