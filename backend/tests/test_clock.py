from app.game.clock import advance_world_time, is_time_regression, parse_world_time, period_label


def test_parse_and_advance():
    assert parse_world_time("Day 1, Morning") == (1, 1)
    assert period_label("Day 1, Morning") == "Morning"
    assert advance_world_time("Day 1, Morning") == "Day 1, Noon"
    assert advance_world_time("Day 1, Midnight") == "Day 2, Dawn"


def test_no_regression():
    assert is_time_regression("Day 3, Morning", "Day 1, Night")
    assert not is_time_regression("Day 1, Morning", "Day 1, Evening")
    assert not is_time_regression("whenever", "later")
