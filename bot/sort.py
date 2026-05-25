from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MergeSortState:
    queue: list[list[int]]
    next_pass: list[list[int]] = field(default_factory=list)
    merge_left: list[int] = field(default_factory=list)
    merge_right: list[int] = field(default_factory=list)
    merged: list[int] = field(default_factory=list)
    finished: bool = False
    final_result: list[int] = field(default_factory=list)

    @classmethod
    def initial(cls, n: int) -> MergeSortState:
        return cls(queue=[[index] for index in range(n)])

    @classmethod
    def from_json(cls, payload: str) -> MergeSortState:
        data: dict[str, Any] = json.loads(payload)
        legacy_runs = data.get("runs")
        if legacy_runs is not None and "queue" not in data:
            return cls(
                queue=[list(run) for run in legacy_runs],
                next_pass=[list(run) for run in data.get("next_runs", [])],
                merge_left=list(data.get("merge_left", [])),
                merge_right=list(data.get("merge_right", [])),
                merged=list(data.get("merged", [])),
                finished=bool(data.get("finished", False)),
                final_result=list(data.get("final_result", [])),
            )

        return cls(
            queue=[list(run) for run in data["queue"]],
            next_pass=[list(run) for run in data.get("next_pass", [])],
            merge_left=list(data.get("merge_left", [])),
            merge_right=list(data.get("merge_right", [])),
            merged=list(data.get("merged", [])),
            finished=bool(data.get("finished", False)),
            final_result=list(data.get("final_result", [])),
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "queue": self.queue,
                "next_pass": self.next_pass,
                "merge_left": self.merge_left,
                "merge_right": self.merge_right,
                "merged": self.merged,
                "finished": self.finished,
                "final_result": self.final_result,
            },
            ensure_ascii=False,
        )

    def current_pair(self) -> tuple[int, int] | None:
        if self.finished:
            return None
        self._prepare_comparison()
        if self.finished or not self.merge_left or not self.merge_right:
            return None
        return self.merge_left[0], self.merge_right[0]

    def step(self, choice: int) -> None:
        if self.finished:
            raise RuntimeError("Sorting is already finished")
        if choice not in (1, 2):
            raise ValueError("Choice must be 1 (left) or 2 (right)")

        self._prepare_comparison()
        if not self.merge_left or not self.merge_right:
            raise RuntimeError("No comparison available")

        if choice == 1:
            self.merged.append(self.merge_left.pop(0))
        else:
            self.merged.append(self.merge_right.pop(0))

        if not self.merge_left or not self.merge_right:
            self._complete_active_merge()

    def is_done(self) -> bool:
        return self.finished

    def result(self) -> list[int]:
        if not self.finished:
            raise RuntimeError("Sorting is not finished yet")
        return list(self.final_result)

    def _prepare_comparison(self) -> None:
        while not self.finished:
            if self.merge_left and self.merge_right:
                return

            if self.merge_left or self.merge_right or self.merged:
                self._complete_active_merge()
                continue

            if len(self.queue) >= 2:
                self.merge_left = self.queue.pop(0)
                self.merge_right = self.queue.pop(0)
                return

            if len(self.queue) == 1:
                self.next_pass.append(self.queue.pop(0))

            if not self.queue:
                self._advance_pass()

    def _complete_active_merge(self) -> None:
        if self.merge_left:
            self.merged.extend(self.merge_left)
            self.merge_left = []
        if self.merge_right:
            self.merged.extend(self.merge_right)
            self.merge_right = []

        self.next_pass.append(self.merged)
        self.merged = []

        if len(self.queue) >= 2:
            self.merge_left = self.queue.pop(0)
            self.merge_right = self.queue.pop(0)
        elif len(self.queue) == 1:
            self.next_pass.append(self.queue.pop(0))
            self.queue = []

        if not self.queue and not self.merge_left and not self.merge_right and not self.merged:
            self._advance_pass()

    def _advance_pass(self) -> None:
        if len(self.next_pass) == 1:
            self.final_result = self.next_pass[0]
            self.finished = True
            self.next_pass = []
            return

        if not self.next_pass:
            self.finished = True
            return

        self.queue = self.next_pass
        self.next_pass = []
