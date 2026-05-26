from __future__ import annotations

import pytest

from bot.core.stages import (
    STAGE_THEMES,
    LowerStage,
    MergeSortStage,
)
from bot.core.values import estimate_comparisons


def test_themes_stage_current_keys() -> None:
    stage = MergeSortStage.create("terminal", STAGE_THEMES, ["A", "B", "C"])
    keys = stage.current_keys()
    assert keys is not None
    assert len(keys) == 2


def test_values_stage_round_trip() -> None:
    stage = MergeSortStage.create("terminal", "values", ["V1", "V2", "V3", "V4"])
    stage.step(1)
    restored = MergeSortStage.from_dict(stage.to_dict())
    assert restored.keys == stage.keys
    assert restored.comparisons == 1


def test_lower_stage_groups_triples() -> None:
    stage = LowerStage.from_value_keys("terminal", ["a", "b", "c", "d", "e"])
    assert len(stage.pending) == 1
    assert stage.auto_survived == ["d", "e"]


def test_lower_stage_step() -> None:
    stage = LowerStage.from_value_keys("terminal", ["a", "b", "c", "d", "e", "f"])
    stage.step(2)
    assert stage.eliminated == ["b"]
    assert set(stage.survived) == {"a", "c"}


def test_lower_stage_invalid_choice() -> None:
    stage = LowerStage.from_value_keys("terminal", ["a", "b", "c"])
    with pytest.raises(ValueError):
        stage.step(4)


def test_estimated_remaining_decreases() -> None:
    stage = MergeSortStage.create("terminal", STAGE_THEMES, ["A", "B", "C", "D"])
    initial = stage.estimated_remaining()
    stage.step(1)
    assert stage.estimated_remaining() <= initial
    assert stage.estimated_remaining() <= estimate_comparisons(4)
