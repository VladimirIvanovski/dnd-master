from app.game.dice import ability_modifier, parse_dice, roll_dice, skill_check
import random


def test_parse_dice():
    assert parse_dice("2d6+3") == (2, 6, 3)
    assert parse_dice("d20") == (1, 20, 0)


def test_roll_dice_deterministic():
    rng = random.Random(1)
    roll = roll_dice("2d6", rng)
    assert len(roll.rolls) == 2
    assert roll.total == sum(roll.rolls)


def test_ability_modifier():
    assert ability_modifier(10) == 0
    assert ability_modifier(14) == 2
    assert ability_modifier(8) == -1


def test_skill_check():
    rng = random.Random(0)
    roll, success = skill_check(18, dc=5, rng=rng)
    assert isinstance(success, bool)
    assert roll.total >= 1
