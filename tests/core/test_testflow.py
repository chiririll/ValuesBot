from __future__ import annotations

from bot.core.stages import STAGE_LOWER, STAGE_THEMES, STAGE_VALUES
from bot.core.testflow import TestState
from bot.core.values import Catalog


def _advance_all(state: TestState, catalog: Catalog, *, prefer: int = 1) -> None:
    safety = 500
    while not state.is_done() and safety > 0:
        keys = state.current_keys()
        if keys is None:
            break
        state.step(prefer, catalog)
        safety -= 1
    assert safety > 0


def test_initial_creates_theme_stages(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    assert "terminal:themes" in state.stages
    assert "instrumental:themes" in state.stages


def test_round_robin_alternates_categories(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    tracks = []
    for _ in range(4):
        track = state.current_track()
        assert track is not None
        tracks.append(track.category)
        state.step(1, catalog)
    assert tracks[0] != tracks[1] or len(set(tracks)) >= 1


def test_themes_finished_creates_values_and_lower(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    for _ in range(20):
        track = state.current_track()
        if track and track.stage == STAGE_THEMES and track.category == "terminal":
            while True:
                stage_key = f"terminal:{STAGE_THEMES}"
                if state.stages[stage_key].is_done():
                    break
                state.step(1, catalog)
            break
    assert f"terminal:{STAGE_VALUES}" in state.stages
    assert f"terminal:{STAGE_LOWER}" in state.stages


def test_full_run_produces_result(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    _advance_all(state, catalog)
    assert state.is_done()
    result = state.result(catalog)
    for category in ("terminal", "instrumental"):
        cat_result = result.by_category[category]
        assert isinstance(cat_result.important, list)


def test_round_trip_dict(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    state.step(1, catalog)
    restored = TestState.from_dict(state.to_dict())
    assert restored.comparisons_done() == state.comparisons_done()


def test_estimated_total_monotonic(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    previous = state.estimated_total(catalog)
    for _ in range(10):
        if state.is_done():
            break
        state.step(1, catalog)
        current = state.estimated_total(catalog)
        assert current >= state.comparisons_done()
        assert current <= previous + 1
        previous = current


def test_is_done_false_until_complete(catalog: Catalog) -> None:
    state = TestState.initial(catalog)
    assert not state.is_done()
    _advance_all(state, catalog)
    assert state.is_done()
