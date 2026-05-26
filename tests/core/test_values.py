from __future__ import annotations

import json
from pathlib import Path

import pytest

from bot.core.values import (
    Catalog,
    estimate_comparisons,
    load_catalog,
    max_lower_triples_count,
    max_top_values_count,
    theme_examples,
)
from tests.conftest import VALUES_FIXTURE


@pytest.mark.parametrize(
    ("n", "expected"),
    [(0, 0), (1, 0), (2, 1), (4, 5), (8, 17)],
)
def test_estimate_comparisons(n: int, expected: int) -> None:
    assert estimate_comparisons(n) == expected


def test_load_catalog_fixture(catalog: Catalog) -> None:
    assert "terminal" in catalog.categories
    assert "instrumental" in catalog.categories
    assert len(catalog.categories["terminal"].theme_keys) == 3


def test_max_top_values_count(catalog: Catalog) -> None:
    assert max_top_values_count(catalog, "terminal") == 7


def test_max_lower_triples_count(catalog: Catalog) -> None:
    # Smallest lower theme has 2 values → 2 // 3 == 0 triples in worst case
    assert max_lower_triples_count(catalog, "terminal") == 0


def test_theme_examples(catalog: Catalog) -> None:
    theme = catalog.themes["Тема A"]
    examples = theme_examples(theme, catalog, 3)
    assert examples == ["A1", "A2", "A3"]


def test_load_empty_raises(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(ValueError, match="No categories"):
        load_catalog(path)


def test_fixture_path_not_prod() -> None:
    assert VALUES_FIXTURE.name == "values.json"
    assert "fixtures" in str(VALUES_FIXTURE)
