from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from bot.core.sort import MergeSortState
from bot.core.values import estimate_comparisons

STAGE_THEMES = "themes"
STAGE_VALUES = "values"
STAGE_LOWER = "lower"

STAGE_TYPE_MERGE = "merge"
STAGE_TYPE_LOWER = "lower"


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


@runtime_checkable
class Stage(Protocol):
    @property
    def track_id(self) -> TrackId: ...

    def as_key(self) -> str: ...

    def current_keys(self) -> tuple[str, ...] | None: ...

    def step(self, choice: int) -> None: ...

    def is_done(self) -> bool: ...

    def comparisons_done(self) -> int: ...

    def estimated_remaining(self) -> int: ...

    def is_pair_stage(self) -> bool: ...

    def to_dict(self) -> dict[str, Any]: ...


@dataclass
class MergeSortStage:
    """Pairwise merge-sort stage for themes or values."""

    category: str
    kind: str
    keys: list[str]
    sort: MergeSortState
    comparisons: int = 0

    @property
    def track_id(self) -> TrackId:
        return TrackId(category=self.category, stage=self.kind)

    def as_key(self) -> str:
        return self.track_id.as_key()

    @classmethod
    def create(cls, category: str, kind: str, keys: list[str]) -> MergeSortStage:
        return cls(
            category=category,
            kind=kind,
            keys=list(keys),
            sort=MergeSortState.initial(len(keys)),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeSortStage:
        return cls(
            category=data["category"],
            kind=data["kind"],
            keys=list(data["keys"]),
            sort=MergeSortState.from_dict(data["sort"]),
            comparisons=int(data.get("comparisons", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": STAGE_TYPE_MERGE,
            "category": self.category,
            "kind": self.kind,
            "keys": self.keys,
            "sort": self.sort.to_dict(),
            "comparisons": self.comparisons,
        }

    def current_keys(self) -> tuple[str, ...] | None:
        pair = self.sort.current_pair()
        if pair is None:
            return None
        return self.keys[pair[0]], self.keys[pair[1]]

    def step(self, choice: int) -> None:
        if choice not in (1, 2):
            raise ValueError("Merge sort step expects choice 1 or 2")
        self.sort.step(choice)
        self.comparisons += 1

    def is_done(self) -> bool:
        return self.sort.is_done()

    def comparisons_done(self) -> int:
        return self.comparisons

    def estimated_remaining(self) -> int:
        if self.is_done():
            return 0
        remaining = estimate_comparisons(len(self.keys)) - self.comparisons
        return max(0, remaining)

    def is_pair_stage(self) -> bool:
        return True

    def ranked_keys(self) -> list[str]:
        indices = self.sort.result()
        return [self.keys[index] for index in indices]


@dataclass
class LowerStage:
    """Triple-elimination stage for lower-theme values."""

    category: str
    pending: list[list[str]] = field(default_factory=list)
    auto_survived: list[str] = field(default_factory=list)
    eliminated: list[str] = field(default_factory=list)
    survived: list[str] = field(default_factory=list)
    comparisons: int = 0

    @property
    def track_id(self) -> TrackId:
        return TrackId(category=self.category, stage=STAGE_LOWER)

    def as_key(self) -> str:
        return self.track_id.as_key()

    @classmethod
    def from_value_keys(cls, category: str, value_keys: list[str]) -> LowerStage:
        triples: list[list[str]] = []
        auto_survived: list[str] = []
        index = 0
        while index + 3 <= len(value_keys):
            triples.append(list(value_keys[index : index + 3]))
            index += 3
        if index < len(value_keys):
            auto_survived.extend(value_keys[index:])
        return cls(category=category, pending=triples, auto_survived=auto_survived)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LowerStage:
        return cls(
            category=data["category"],
            pending=[list(triple) for triple in data.get("pending", [])],
            auto_survived=list(data.get("auto_survived", [])),
            eliminated=list(data.get("eliminated", [])),
            survived=list(data.get("survived", [])),
            comparisons=int(data.get("comparisons", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": STAGE_TYPE_LOWER,
            "category": self.category,
            "pending": self.pending,
            "auto_survived": self.auto_survived,
            "eliminated": self.eliminated,
            "survived": self.survived,
            "comparisons": self.comparisons,
        }

    def current_keys(self) -> tuple[str, ...] | None:
        if not self.pending:
            return None
        return tuple(self.pending[0])

    def step(self, choice: int) -> None:
        if choice not in (1, 2, 3):
            raise ValueError("Lower step expects choice 1, 2 or 3")
        triple = self.pending.pop(0)
        eliminated_key = triple[choice - 1]
        survived_keys = [key for index, key in enumerate(triple) if index != choice - 1]
        self.eliminated.append(eliminated_key)
        self.survived.extend(survived_keys)
        self.comparisons += 1

    def is_done(self) -> bool:
        return not self.pending

    def comparisons_done(self) -> int:
        return self.comparisons

    def estimated_remaining(self) -> int:
        return len(self.pending)

    def is_pair_stage(self) -> bool:
        return False

    def also_important_keys(self) -> list[str]:
        return list(self.survived) + list(self.auto_survived)


def stage_from_dict(data: dict[str, Any]) -> Stage:
    stage_type = data.get("type")
    if stage_type == STAGE_TYPE_MERGE:
        return MergeSortStage.from_dict(data)
    if stage_type == STAGE_TYPE_LOWER:
        return LowerStage.from_dict(data)
    raise ValueError(f"Unknown stage type: {stage_type}")
