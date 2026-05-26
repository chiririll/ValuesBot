from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from bot.core.stages import (
    STAGE_LOWER,
    STAGE_THEMES,
    STAGE_VALUES,
    LowerStage,
    MergeSortStage,
    Stage,
    TrackId,
    stage_from_dict,
)
from bot.core.values import (
    CATEGORY_ORDER,
    TOP_THEMES_COUNT,
    Catalog,
    estimate_comparisons,
    max_lower_triples_count,
    max_top_values_count,
)


@dataclass
class CategoryResult:
    important: list[str]
    also_important: list[str]
    less_important: list[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "important": self.important,
            "also_important": self.also_important,
            "less_important": self.less_important,
        }

    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> CategoryResult:
        return cls(
            important=list(data.get("important", [])),
            also_important=list(data.get("also_important", [])),
            less_important=list(data.get("less_important", [])),
        )


@dataclass
class TestResult:
    by_category: dict[str, CategoryResult]

    def to_dict(self) -> dict[str, dict[str, list[str]]]:
        return {key: value.to_dict() for key, value in self.by_category.items()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, list[str]]]) -> TestResult:
        return cls(
            by_category={key: CategoryResult.from_dict(value) for key, value in data.items()}
        )


@dataclass
class TestState:
    stages: dict[str, Stage]
    theme_ranks: dict[str, list[str]] = field(default_factory=dict)
    cursor: int = 0

    @classmethod
    def initial(cls, catalog: Catalog) -> TestState:
        stages: dict[str, Stage] = {}
        for category_key in CATEGORY_ORDER:
            theme_keys = list(catalog.categories[category_key].theme_keys)
            stage = MergeSortStage.create(category_key, STAGE_THEMES, theme_keys)
            stages[stage.as_key()] = stage
        return cls(stages=stages)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestState:
        stages = {key: stage_from_dict(value) for key, value in data["stages"].items()}
        return cls(
            stages=stages,
            theme_ranks={key: list(value) for key, value in data.get("theme_ranks", {}).items()},
            cursor=int(data.get("cursor", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": {key: stage.to_dict() for key, stage in self.stages.items()},
            "theme_ranks": self.theme_ranks,
            "cursor": self.cursor,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, payload: str) -> TestState:
        return cls.from_dict(json.loads(payload))

    def comparisons_done(self) -> int:
        return sum(stage.comparisons_done() for stage in self.stages.values())

    def _active_stage_keys(self) -> list[str]:
        active = [key for key, stage in self.stages.items() if not stage.is_done()]
        pair_active = [key for key in active if self.stages[key].is_pair_stage()]
        if pair_active:
            return pair_active
        return active

    def current_track(self) -> TrackId | None:
        active = self._active_stage_keys()
        if not active:
            return None
        index = self.cursor % len(active)
        return self.stages[active[index]].track_id

    def current_keys(self) -> tuple[str, ...] | None:
        active = self._active_stage_keys()
        if not active:
            return None
        index = self.cursor % len(active)
        return self.stages[active[index]].current_keys()

    def step(self, choice: int, catalog: Catalog) -> None:
        active = self._active_stage_keys()
        if not active:
            raise RuntimeError("No active stage")

        index = self.cursor % len(active)
        stage_key = active[index]
        stage = self.stages[stage_key]
        stage.step(choice)

        if stage.track_id.stage == STAGE_THEMES and stage.is_done():
            self._on_themes_finished(stage.track_id.category, catalog)

        active_after = self._active_stage_keys()
        if active_after:
            if stage_key in active_after:
                new_index = active_after.index(stage_key)
            else:
                new_index = min(self.cursor, len(active_after) - 1)
            self.cursor = (new_index + 1) % len(active_after)

    def _on_themes_finished(self, category: str, catalog: Catalog) -> None:
        themes_key = f"{category}:{STAGE_THEMES}"
        themes_stage = self.stages[themes_key]
        assert isinstance(themes_stage, MergeSortStage)
        ranked_theme_keys = themes_stage.ranked_keys()
        self.theme_ranks[category] = ranked_theme_keys

        top_themes = ranked_theme_keys[:TOP_THEMES_COUNT]
        lower_themes = ranked_theme_keys[TOP_THEMES_COUNT:]

        top_value_keys: list[str] = []
        for theme_key in top_themes:
            top_value_keys.extend(catalog.themes[theme_key].value_keys)

        values_stage = MergeSortStage.create(category, STAGE_VALUES, top_value_keys)
        self.stages[values_stage.as_key()] = values_stage

        lower_value_keys: list[str] = []
        for theme_key in lower_themes:
            lower_value_keys.extend(catalog.themes[theme_key].value_keys)

        lower_stage = LowerStage.from_value_keys(category, lower_value_keys)
        self.stages[lower_stage.as_key()] = lower_stage

    def is_done(self) -> bool:
        for category_key in CATEGORY_ORDER:
            values_key = f"{category_key}:{STAGE_VALUES}"
            lower_key = f"{category_key}:{STAGE_LOWER}"
            if values_key not in self.stages or not self.stages[values_key].is_done():
                return False
            if lower_key not in self.stages or not self.stages[lower_key].is_done():
                return False
        return True

    def result(self, catalog: Catalog) -> TestResult:
        del catalog
        by_category: dict[str, CategoryResult] = {}

        for category_key in CATEGORY_ORDER:
            values_key = f"{category_key}:{STAGE_VALUES}"
            important: list[str] = []
            values_stage = self.stages.get(values_key)
            if isinstance(values_stage, MergeSortStage) and values_stage.is_done():
                important = values_stage.ranked_keys()

            lower_key = f"{category_key}:{STAGE_LOWER}"
            lower_stage = self.stages.get(lower_key)
            if isinstance(lower_stage, LowerStage):
                also_important = lower_stage.also_important_keys()
                less_important = list(lower_stage.eliminated)
            else:
                also_important = []
                less_important = []

            by_category[category_key] = CategoryResult(
                important=important,
                also_important=also_important,
                less_important=less_important,
            )

        return TestResult(by_category=by_category)

    def estimated_total(self, catalog: Catalog) -> int:
        total = self.comparisons_done()

        for category_key in CATEGORY_ORDER:
            themes_key = f"{category_key}:{STAGE_THEMES}"
            values_key = f"{category_key}:{STAGE_VALUES}"
            lower_key = f"{category_key}:{STAGE_LOWER}"

            themes_stage = self.stages.get(themes_key)
            if themes_stage is not None and not themes_stage.is_done():
                total += themes_stage.estimated_remaining()

            themes_known = category_key in self.theme_ranks

            values_stage = self.stages.get(values_key)
            if values_stage is not None:
                if not values_stage.is_done():
                    total += values_stage.estimated_remaining()
            elif not themes_known:
                total += estimate_comparisons(max_top_values_count(catalog, category_key))

            lower_stage = self.stages.get(lower_key)
            if isinstance(lower_stage, LowerStage):
                total += lower_stage.estimated_remaining()
            elif not themes_known:
                total += max_lower_triples_count(catalog, category_key)

        return total
