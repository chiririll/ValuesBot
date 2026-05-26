from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from bot.sort import MergeSortState
from bot.values import (
    CATEGORY_ORDER,
    TOP_THEMES_COUNT,
    Catalog,
    estimate_comparisons,
    max_lower_triples_count,
    max_top_values_count,
)

STAGE_THEMES = "themes"
STAGE_VALUES = "values"
STAGE_LOWER = "lower"


@dataclass(frozen=True, slots=True)
class TrackId:
    category: str
    stage: str

    def as_key(self) -> str:
        return f"{self.category}:{self.stage}"

    @classmethod
    def from_key(cls, key: str) -> TrackId:
        category, stage = key.split(":", maxsplit=1)
        return cls(category=category, stage=stage)


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
            by_category={
                key: CategoryResult.from_dict(value) for key, value in data.items()
            }
        )


@dataclass
class LowerState:
    """Triple-elimination state for the lower-themes pool of one category."""

    pending: list[list[str]] = field(default_factory=list)
    auto_survived: list[str] = field(default_factory=list)
    eliminated: list[str] = field(default_factory=list)
    survived: list[str] = field(default_factory=list)

    def is_done(self) -> bool:
        return not self.pending

    def current_triple(self) -> list[str] | None:
        return self.pending[0] if self.pending else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pending": self.pending,
            "auto_survived": self.auto_survived,
            "eliminated": self.eliminated,
            "survived": self.survived,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LowerState:
        return cls(
            pending=[list(triple) for triple in data.get("pending", [])],
            auto_survived=list(data.get("auto_survived", [])),
            eliminated=list(data.get("eliminated", [])),
            survived=list(data.get("survived", [])),
        )


@dataclass
class TestState:
    track_keys: dict[str, list[str]]
    tracks: dict[str, MergeSortState]
    theme_ranks: dict[str, list[str]]
    track_comparisons: dict[str, int]
    lower_states: dict[str, LowerState] = field(default_factory=dict)
    cursor: int = 0

    @classmethod
    def initial(cls, catalog: Catalog) -> TestState:
        track_keys: dict[str, list[str]] = {}
        tracks: dict[str, MergeSortState] = {}

        for category_key in CATEGORY_ORDER:
            theme_keys = list(catalog.categories[category_key].theme_keys)
            track_key = f"{category_key}:{STAGE_THEMES}"
            track_keys[track_key] = theme_keys
            tracks[track_key] = MergeSortState.initial(len(theme_keys))

        return cls(
            track_keys=track_keys,
            tracks=tracks,
            theme_ranks={},
            track_comparisons={key: 0 for key in tracks},
            lower_states={},
        )

    @classmethod
    def from_json(cls, payload: str) -> TestState:
        data: dict[str, Any] = json.loads(payload)
        tracks = {
            key: MergeSortState.from_json(value)
            for key, value in data["tracks"].items()
        }
        return cls(
            track_keys={key: list(value) for key, value in data["track_keys"].items()},
            tracks=tracks,
            theme_ranks={
                key: list(value) for key, value in data.get("theme_ranks", {}).items()
            },
            track_comparisons={
                key: int(value)
                for key, value in data.get("track_comparisons", {}).items()
            },
            lower_states={
                key: LowerState.from_dict(value)
                for key, value in data.get("lower_states", {}).items()
            },
            cursor=int(data.get("cursor", 0)),
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "track_keys": self.track_keys,
                "tracks": {key: track.to_json() for key, track in self.tracks.items()},
                "theme_ranks": self.theme_ranks,
                "track_comparisons": self.track_comparisons,
                "lower_states": {
                    key: state.to_dict() for key, state in self.lower_states.items()
                },
                "cursor": self.cursor,
            },
            ensure_ascii=False,
        )

    def comparisons_done(self) -> int:
        return sum(self.track_comparisons.values())

    def _is_track_done(self, track_key: str) -> bool:
        track_id = TrackId.from_key(track_key)
        if track_id.stage == STAGE_LOWER:
            return self.lower_states[track_id.category].is_done()
        return self.tracks[track_key].is_done()

    def _all_track_keys(self) -> list[str]:
        keys = list(self.tracks.keys())
        for category_key, _ in self.lower_states.items():
            keys.append(f"{category_key}:{STAGE_LOWER}")
        return keys

    def _active_track_keys(self) -> list[str]:
        active = [key for key in self._all_track_keys() if not self._is_track_done(key)]

        pair_stage_active = [
            key
            for key in active
            if TrackId.from_key(key).stage in (STAGE_THEMES, STAGE_VALUES)
        ]
        if pair_stage_active:
            return pair_stage_active
        return active

    def current_track(self) -> TrackId | None:
        active = self._active_track_keys()
        if not active:
            return None
        index = self.cursor % len(active)
        return TrackId.from_key(active[index])

    def current_keys(self) -> tuple[str, ...] | None:
        """Return the keys (2 or 3) currently being compared."""
        track = self.current_track()
        if track is None:
            return None

        if track.stage == STAGE_LOWER:
            triple = self.lower_states[track.category].current_triple()
            return tuple(triple) if triple is not None else None

        track_key = track.as_key()
        sort_state = self.tracks[track_key]
        pair = sort_state.current_pair()
        if pair is None:
            return None
        keys = self.track_keys[track_key]
        return keys[pair[0]], keys[pair[1]]

    def step(self, choice: int, catalog: Catalog) -> None:
        track = self.current_track()
        if track is None:
            raise RuntimeError("No active track")

        track_key = track.as_key()

        if track.stage == STAGE_LOWER:
            self._step_lower(track.category, choice)
        else:
            self._step_sort(track_key, choice)

        if track.stage == STAGE_THEMES and self.tracks[track_key].is_done():
            self._on_themes_finished(track.category, catalog)

        active = self._active_track_keys()
        if active:
            if track_key in active:
                index = active.index(track_key)
            else:
                index = min(self.cursor, len(active) - 1)
            self.cursor = (index + 1) % len(active)

    def _step_sort(self, track_key: str, choice: int) -> None:
        if choice not in (1, 2):
            raise ValueError("Sort step expects choice 1 or 2")
        sort_state = self.tracks[track_key]
        sort_state.step(choice)
        self.track_comparisons[track_key] = self.track_comparisons.get(track_key, 0) + 1

    def _step_lower(self, category: str, choice: int) -> None:
        if choice not in (1, 2, 3):
            raise ValueError("Lower step expects choice 1, 2 or 3")
        lower = self.lower_states[category]
        triple = lower.pending.pop(0)
        eliminated_key = triple[choice - 1]
        survived_keys = [key for index, key in enumerate(triple) if index != choice - 1]
        lower.eliminated.append(eliminated_key)
        lower.survived.extend(survived_keys)
        track_key = f"{category}:{STAGE_LOWER}"
        self.track_comparisons[track_key] = self.track_comparisons.get(track_key, 0) + 1

    def _on_themes_finished(self, category: str, catalog: Catalog) -> None:
        themes_key = f"{category}:{STAGE_THEMES}"
        ranked_indices = self.tracks[themes_key].result()
        ranked_theme_keys = [self.track_keys[themes_key][index] for index in ranked_indices]
        self.theme_ranks[category] = ranked_theme_keys

        top_themes = ranked_theme_keys[:TOP_THEMES_COUNT]
        lower_themes = ranked_theme_keys[TOP_THEMES_COUNT:]

        top_value_keys: list[str] = []
        for theme_key in top_themes:
            top_value_keys.extend(catalog.themes[theme_key].value_keys)

        values_key = f"{category}:{STAGE_VALUES}"
        self.track_keys[values_key] = top_value_keys
        self.tracks[values_key] = MergeSortState.initial(len(top_value_keys))
        self.track_comparisons[values_key] = 0

        lower_value_keys: list[str] = []
        for theme_key in lower_themes:
            lower_value_keys.extend(catalog.themes[theme_key].value_keys)

        triples: list[list[str]] = []
        auto_survived: list[str] = []
        index = 0
        while index + 3 <= len(lower_value_keys):
            triples.append(list(lower_value_keys[index : index + 3]))
            index += 3
        if index < len(lower_value_keys):
            auto_survived.extend(lower_value_keys[index:])

        lower_track_key = f"{category}:{STAGE_LOWER}"
        self.track_comparisons[lower_track_key] = 0
        self.lower_states[category] = LowerState(
            pending=triples,
            auto_survived=auto_survived,
        )

    def is_done(self) -> bool:
        for category_key in CATEGORY_ORDER:
            values_key = f"{category_key}:{STAGE_VALUES}"
            if values_key not in self.tracks:
                return False
            if not self.tracks[values_key].is_done():
                return False
            if (
                category_key not in self.lower_states
                or not self.lower_states[category_key].is_done()
            ):
                return False
        return True

    def result(self, catalog: Catalog) -> TestResult:
        by_category: dict[str, CategoryResult] = {}

        for category_key in CATEGORY_ORDER:
            values_key = f"{category_key}:{STAGE_VALUES}"
            important: list[str] = []
            if values_key in self.tracks and self.tracks[values_key].is_done():
                ranked_indices = self.tracks[values_key].result()
                value_keys = self.track_keys[values_key]
                important = [value_keys[index] for index in ranked_indices]

            lower = self.lower_states.get(category_key, LowerState())
            also_important = list(lower.survived) + list(lower.auto_survived)
            less_important = list(lower.eliminated)

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

            if themes_key in self.tracks and not self.tracks[themes_key].is_done():
                remaining = estimate_comparisons(len(self.track_keys[themes_key]))
                remaining -= self.track_comparisons.get(themes_key, 0)
                total += max(0, remaining)

            themes_known = category_key in self.theme_ranks

            if values_key in self.tracks:
                if not self.tracks[values_key].is_done():
                    remaining = estimate_comparisons(len(self.track_keys[values_key]))
                    remaining -= self.track_comparisons.get(values_key, 0)
                    total += max(0, remaining)
            elif not themes_known:
                total += estimate_comparisons(max_top_values_count(catalog, category_key))

            if category_key in self.lower_states:
                lower = self.lower_states[category_key]
                total += len(lower.pending)
            elif not themes_known:
                total += max_lower_triples_count(catalog, category_key)

        return total
