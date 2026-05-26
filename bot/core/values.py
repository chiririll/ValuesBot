from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CATEGORY_ORDER = ("terminal", "instrumental")
TOP_THEMES_COUNT = 2


@dataclass(frozen=True, slots=True)
class ValueItem:
    key: str
    name: str
    description: str
    theme_key: str
    category_key: str


@dataclass(frozen=True, slots=True)
class Theme:
    key: str
    name: str
    value_keys: list[str]
    category_key: str


@dataclass(frozen=True, slots=True)
class Category:
    key: str
    name: str
    description: str
    theme_keys: list[str]


@dataclass(frozen=True, slots=True)
class Catalog:
    categories: dict[str, Category]
    themes: dict[str, Theme]
    values: dict[str, ValueItem]


def estimate_comparisons(n: int) -> int:
    """Worst-case number of comparisons for merge sort on n items."""
    if n <= 1:
        return 0

    levels = 0
    size = 1
    while size < n:
        size <<= 1
        levels += 1

    return n * levels - (1 << levels) + 1


def load_catalog(path: Path) -> Catalog:
    raw = json.loads(path.read_text(encoding="utf-8"))

    categories: dict[str, Category] = {}
    themes: dict[str, Theme] = {}
    values: dict[str, ValueItem] = {}

    for category_key, category_data in raw.items():
        theme_keys: list[str] = []

        for group in category_data["groups"]:
            theme_name = group["name"]
            theme_keys.append(theme_name)
            value_keys: list[str] = []

            for value_name, description in group["values"].items():
                value_keys.append(value_name)
                values[value_name] = ValueItem(
                    key=value_name,
                    name=value_name,
                    description=description,
                    theme_key=theme_name,
                    category_key=category_key,
                )

            themes[theme_name] = Theme(
                key=theme_name,
                name=theme_name,
                value_keys=value_keys,
                category_key=category_key,
            )

        categories[category_key] = Category(
            key=category_key,
            name=category_data["name"],
            description=category_data["description"],
            theme_keys=theme_keys,
        )

    if not categories:
        raise ValueError(f"No categories found in {path}")

    return Catalog(categories=categories, themes=themes, values=values)


def theme_examples(theme: Theme, catalog: Catalog, n: int = 3) -> list[str]:
    return [catalog.values[key].name for key in theme.value_keys[:n]]


def max_top_values_count(catalog: Catalog, category_key: str) -> int:
    category = catalog.categories[category_key]
    sizes = sorted(
        (len(catalog.themes[theme_key].value_keys) for theme_key in category.theme_keys),
        reverse=True,
    )
    return sum(sizes[:TOP_THEMES_COUNT])


def max_lower_triples_count(catalog: Catalog, category_key: str) -> int:
    category = catalog.categories[category_key]
    sizes = sorted(len(catalog.themes[theme_key].value_keys) for theme_key in category.theme_keys)
    lower_total = sum(sizes[: max(0, len(sizes) - TOP_THEMES_COUNT)])
    return lower_total // 3


def initial_estimated_total(catalog: Catalog) -> int:
    total = 0
    for category_key in CATEGORY_ORDER:
        category = catalog.categories[category_key]
        total += estimate_comparisons(len(category.theme_keys))
        total += estimate_comparisons(max_top_values_count(catalog, category_key))
        total += max_lower_triples_count(catalog, category_key)
    return total
