"""Validate the production catalog at data/values.json.

These tests guard against accidental data corruption: missing categories,
duplicate theme or value names (which would silently overwrite entries
in the flat dicts of Catalog), empty descriptions, etc.
"""

from __future__ import annotations

import json

import pytest

from bot.config import DEFAULT_VALUES_PATH
from bot.core.values import (
    CATEGORY_ORDER,
    TOP_THEMES_COUNT,
    Catalog,
    initial_estimated_total,
    load_catalog,
)

WORST_CASE_QUESTIONS_HARD_LIMIT = 150


@pytest.fixture(scope="module")
def raw_data() -> dict:
    return json.loads(DEFAULT_VALUES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def prod_catalog() -> Catalog:
    return load_catalog(DEFAULT_VALUES_PATH)


def test_file_exists() -> None:
    assert DEFAULT_VALUES_PATH.is_file(), f"Missing production catalog at {DEFAULT_VALUES_PATH}"


def test_file_is_valid_utf8_json(raw_data: dict) -> None:
    assert isinstance(raw_data, dict)


def test_loads_without_error(prod_catalog: Catalog) -> None:
    assert isinstance(prod_catalog, Catalog)


def test_both_categories_present(prod_catalog: Catalog) -> None:
    for category_key in CATEGORY_ORDER:
        assert category_key in prod_catalog.categories, (
            f"Category '{category_key}' is missing from the production catalog"
        )


def test_no_unexpected_categories(raw_data: dict) -> None:
    extra = set(raw_data.keys()) - set(CATEGORY_ORDER)
    assert not extra, f"Unexpected categories in catalog: {extra}"


@pytest.mark.parametrize("category_key", CATEGORY_ORDER)
def test_category_has_non_empty_name_and_description(
    prod_catalog: Catalog, category_key: str
) -> None:
    category = prod_catalog.categories[category_key]
    assert category.name.strip(), f"Category '{category_key}' has empty name"
    assert category.description.strip(), f"Category '{category_key}' has empty description"


@pytest.mark.parametrize("category_key", CATEGORY_ORDER)
def test_category_has_enough_themes(prod_catalog: Catalog, category_key: str) -> None:
    """A category must have at least TOP_THEMES_COUNT themes; otherwise the
    top/lower split degenerates."""
    category = prod_catalog.categories[category_key]
    assert len(category.theme_keys) >= TOP_THEMES_COUNT, (
        f"Category '{category_key}' has only {len(category.theme_keys)} theme(s), "
        f"need at least {TOP_THEMES_COUNT}"
    )


def test_theme_names_are_globally_unique(raw_data: dict) -> None:
    """Catalog.themes is a flat dict keyed by theme name — duplicates would
    silently overwrite earlier entries."""
    seen: list[str] = []
    for category_data in raw_data.values():
        for group in category_data["groups"]:
            seen.append(group["name"])
    duplicates = {name for name in seen if seen.count(name) > 1}
    assert not duplicates, f"Duplicate theme names across catalog: {duplicates}"


def test_value_names_are_globally_unique(raw_data: dict) -> None:
    """Catalog.values is a flat dict keyed by value name — duplicates would
    silently overwrite earlier entries and break the algorithm."""
    seen: list[str] = []
    for category_data in raw_data.values():
        for group in category_data["groups"]:
            seen.extend(group["values"].keys())
    duplicates = {name for name in seen if seen.count(name) > 1}
    assert not duplicates, f"Duplicate value names across catalog: {duplicates}"


def test_themes_have_non_empty_names_and_values(prod_catalog: Catalog) -> None:
    for theme in prod_catalog.themes.values():
        assert theme.name.strip(), "Theme has empty name"
        assert theme.value_keys, f"Theme '{theme.name}' has no values"


def test_values_have_non_empty_descriptions(prod_catalog: Catalog) -> None:
    for value in prod_catalog.values.values():
        assert value.description.strip(), f"Value '{value.name}' has empty description"


def test_value_backrefs_consistent(prod_catalog: Catalog) -> None:
    """Every value must point back to a theme and category that actually exists."""
    for value in prod_catalog.values.values():
        assert value.theme_key in prod_catalog.themes
        assert value.category_key in prod_catalog.categories
        theme = prod_catalog.themes[value.theme_key]
        assert value.key in theme.value_keys
        assert theme.category_key == value.category_key


def test_worst_case_question_count_is_reasonable(prod_catalog: Catalog) -> None:
    """README promises ~100 questions in the worst case. Guard against
    accidentally bloating the catalog past a sensible UX limit."""
    total = initial_estimated_total(prod_catalog)
    assert total <= WORST_CASE_QUESTIONS_HARD_LIMIT, (
        f"Worst-case question count is {total}, exceeds limit of {WORST_CASE_QUESTIONS_HARD_LIMIT}"
    )


def test_category_keys_in_expected_order(raw_data: dict) -> None:
    """JSON dict order is preserved in Python 3.7+; categories should appear
    in CATEGORY_ORDER so that the test starts with terminal values."""
    assert tuple(raw_data.keys()) == CATEGORY_ORDER
