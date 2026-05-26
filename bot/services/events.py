from __future__ import annotations

from dataclasses import dataclass

from bot.core.stages import TrackId
from bot.core.testflow import TestResult


@dataclass(frozen=True, slots=True)
class Welcome:
    estimated_total: int


@dataclass(frozen=True, slots=True)
class Resume:
    comparisons_done: int
    estimated_total: int


@dataclass(frozen=True, slots=True)
class Question:
    track: TrackId
    keys: tuple[str, ...]
    comparisons_done: int
    estimated_total: int


@dataclass(frozen=True, slots=True)
class Finished:
    result: TestResult


@dataclass(frozen=True, slots=True)
class AlreadyFinished:
    pass


@dataclass(frozen=True, slots=True)
class NoResult:
    pass


@dataclass(frozen=True, slots=True)
class UndoUnavailable:
    pass


@dataclass(frozen=True, slots=True)
class RestartConfirm:
    pass


SessionEvent = (
    Welcome
    | Resume
    | Question
    | Finished
    | AlreadyFinished
    | NoResult
    | UndoUnavailable
    | RestartConfirm
)
