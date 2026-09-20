from __future__ import annotations

import re

PERIODS = {
    "dawn": 0,
    "morning": 1,
    "noon": 2,
    "afternoon": 3,
    "evening": 4,
    "dusk": 5,
    "night": 6,
    "midnight": 7,
}

PERIOD_NAMES = [
    "Dawn",
    "Morning",
    "Noon",
    "Afternoon",
    "Evening",
    "Dusk",
    "Night",
    "Midnight",
]

_RE = re.compile(r"Day\s+(\d+)\s*,\s*([A-Za-z]+)", re.IGNORECASE)


def parse_world_time(text: str) -> tuple[int, int] | None:
    match = _RE.search(text or "")
    if not match:
        return None
    period = PERIODS.get(match.group(2).lower())
    if period is None:
        return None
    return int(match.group(1)), period


def period_label(text: str) -> str | None:
    parsed = parse_world_time(text)
    if parsed is None:
        return None
    return PERIOD_NAMES[parsed[1]]


def time_ordinal(text: str) -> int | None:
    parsed = parse_world_time(text)
    if parsed is None:
        return None
    day, period = parsed
    return day * len(PERIOD_NAMES) + period


def is_time_regression(old: str, new: str) -> bool:
    a = time_ordinal(old)
    b = time_ordinal(new)
    if a is None or b is None:
        return False
    return b < a


def advance_world_time(current: str, steps: int = 1) -> str:
    parsed = parse_world_time(current) or (1, PERIODS["morning"])
    day, period = parsed
    total = day * len(PERIOD_NAMES) + period + max(1, steps)
    period = total % len(PERIOD_NAMES)
    day = max(1, total // len(PERIOD_NAMES))
    if period == 0:
        # midnight of previous packing: Day N, Midnight is index 7
        pass
    return f"Day {day}, {PERIOD_NAMES[period]}"
