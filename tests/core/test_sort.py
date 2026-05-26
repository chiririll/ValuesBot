from __future__ import annotations

import random
from collections.abc import Callable

import pytest

from bot.core.sort import MergeSortState
from bot.core.values import estimate_comparisons


def _run_sort(n: int, *, prefer_left: bool) -> list[int]:
    state = MergeSortState.initial(n)
    steps = 0
    max_steps = estimate_comparisons(n) + n + 5
    while not state.is_done() and steps < max_steps:
        pair = state.current_pair()
        if pair is None:
            break
        state.step(1 if prefer_left else 2)
        steps += 1
    return state.result()


@pytest.mark.parametrize("n", [0, 1, 2, 3, 4, 7, 8])
def test_initial_sizes(n: int) -> None:
    state = MergeSortState.initial(n)
    assert len(state.queue) == n


def test_left_preference_preserves_order() -> None:
    for n in range(2, 9):
        assert _run_sort(n, prefer_left=True) == list(range(n))


def test_right_preference_reverses() -> None:
    for n in range(2, 9):
        assert _run_sort(n, prefer_left=False) == list(reversed(range(n)))


def test_random_permutation_property() -> None:
    rng = random.Random(42)
    for n in range(2, 8):
        indices = list(range(n))
        rng.shuffle(indices)
        comparator: dict[tuple[int, int], bool] = {}

        def make_compare(
            order: list[int], cache: dict[tuple[int, int], bool]
        ) -> Callable[[int, int], bool]:
            def compare(i: int, j: int) -> bool:
                key = (i, j)
                if key not in cache:
                    cache[key] = order[i] < order[j]
                return cache[key]

            return compare

        compare = make_compare(indices, comparator)

        state = MergeSortState.initial(n)
        steps = 0
        while not state.is_done() and steps < 200:
            pair = state.current_pair()
            if pair is None:
                break
            left, right = pair
            state.step(1 if compare(left, right) else 2)
            steps += 1

        ranked = state.result()
        assert ranked == sorted(range(n), key=lambda i: indices[i])


def test_round_trip_dict() -> None:
    state = MergeSortState.initial(5)
    state.step(1)
    restored = MergeSortState.from_dict(state.to_dict())
    assert restored.queue == state.queue
    assert restored.merge_left == state.merge_left


def test_no_pair_after_done() -> None:
    state = MergeSortState.initial(3)
    while not state.is_done():
        pair = state.current_pair()
        if pair is None:
            break
        state.step(1)
    assert state.current_pair() is None


def test_steps_within_worst_case() -> None:
    n = 8
    state = MergeSortState.initial(n)
    steps = 0
    while not state.is_done():
        pair = state.current_pair()
        if pair is None:
            break
        state.step(1)
        steps += 1
    assert steps <= estimate_comparisons(n)


def test_result_before_done_raises() -> None:
    state = MergeSortState.initial(3)
    with pytest.raises(RuntimeError):
        state.result()
