from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bot.config import VALUES_PATH

VALUE_PATTERN = re.compile(r"^(?P<name>[^(]+?)\s*\((?P<desc>.+)\)\s*$")


@dataclass(frozen=True, slots=True)
class Value:
    name: str
    description: str


def to_sentence_case(text: str) -> str:
    normalized = text.strip().lower()
    if not normalized:
        return normalized
    return normalized[:1].upper() + normalized[1:]


def load_values(path: Path | None = None) -> list[Value]:
    source = path or VALUES_PATH
    values: list[Value] = []

    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = VALUE_PATTERN.match(line)
        if not match:
            raise ValueError(f"Invalid value line: {raw_line!r}")

        values.append(
            Value(
                name=to_sentence_case(match.group("name")),
                description=match.group("desc").strip(),
            )
        )

    if not values:
        raise ValueError(f"No values found in {source}")

    return values


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
