from __future__ import annotations

import random
import re
from dataclasses import dataclass


DICE_RE = re.compile(r"^\s*(\d*)d(\d+)([+-]\d+)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class DiceRoll:
    notation: str
    rolls: list[int]
    modifier: int
    total: int


def parse_dice(notation: str) -> tuple[int, int, int]:
    match = DICE_RE.match(notation)
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")
    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int(match.group(3) or "0")
    if count < 1 or sides < 2 or count > 100:
        raise ValueError(f"Invalid dice notation: {notation}")
    return count, sides, modifier


def roll_dice(notation: str, rng: random.Random | None = None) -> DiceRoll:
    rng = rng or random.Random()
    count, sides, modifier = parse_dice(notation)
    rolls = [rng.randint(1, sides) for _ in range(count)]
    return DiceRoll(notation=notation, rolls=rolls, modifier=modifier, total=sum(rolls) + modifier)


def roll_d20(rng: random.Random | None = None) -> DiceRoll:
    return roll_dice("1d20", rng)


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def skill_check(
    ability_score: int,
    dc: int,
    *,
    proficiency_bonus: int = 0,
    rng: random.Random | None = None,
) -> tuple[DiceRoll, bool]:
    roll = roll_d20(rng)
    total = roll.total + ability_modifier(ability_score) + proficiency_bonus
    adjusted = DiceRoll(
        notation=roll.notation,
        rolls=roll.rolls,
        modifier=roll.modifier + ability_modifier(ability_score) + proficiency_bonus,
        total=total,
    )
    return adjusted, total >= dc
