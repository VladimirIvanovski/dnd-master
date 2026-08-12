from uuid import uuid4

from app.schemas.gameplay import DiceResultOut, PlayerActionRequest, StateChange
from app.schemas.state import CharacterState, GameState
from app.services.gameplay import GameplayService


def _state(**kwargs) -> GameState:
    ch = CharacterState(
        id=uuid4(),
        name="Vesper",
        race="Human",
        class_name="Rogue",
        level=1,
        xp=0,
        hp=10,
        max_hp=10,
        ac=12,
        gold=0,
        abilities={},
    )
    return GameState(
        campaign_id=uuid4(),
        campaign_name="Cursed Dunes",
        character=ch,
        current_time="Day 1, Morning",
        weather="clear",
        world_state={},
        nearby_npcs=[],
        active_quests=[],
        inventory=[],
        combat=kwargs.get("combat"),
        current_location=None,
    )


def test_fallback_starts_quest_on_accept_bargain():
    req = PlayerActionRequest(
        campaign_id=uuid4(),
        character_id=uuid4(),
        action="Accept Mira's trade and offer a sacrifice",
    )
    out = GameplayService._mechanical_fallbacks(_state(), req, [], [])
    assert any(c.action == "start_quest" for c in out)
    quest = next(c for c in out if c.action == "start_quest")
    assert quest.params["title"] == "Mira's Bargain"
    assert quest.params["reward_xp"] == 75


def test_fallback_skips_quest_if_dm_already_started():
    req = PlayerActionRequest(
        campaign_id=uuid4(),
        character_id=uuid4(),
        action="Accept Mira's trade",
    )
    existing = [StateChange(action="start_quest", params={"title": "Already", "objectives": []})]
    out = GameplayService._mechanical_fallbacks(_state(), req, [], existing)
    assert sum(1 for c in out if c.action == "start_quest") == 1


def test_fallback_applies_damage_on_failed_hostile_check():
    req = PlayerActionRequest(
        campaign_id=uuid4(),
        character_id=uuid4(),
        action="Attack the sand creature",
    )
    dice = [
        DiceResultOut(
            notation="1d20",
            purpose="attack",
            natural=4,
            rolls=[4],
            modifier=0,
            total=4,
            dc=12,
            success=False,
        )
    ]
    out = GameplayService._mechanical_fallbacks(_state(), req, dice, [])
    assert any(c.action == "apply_damage" and c.params.get("amount") == 1 for c in out)


def test_fallback_no_damage_without_fail():
    req = PlayerActionRequest(
        campaign_id=uuid4(),
        character_id=uuid4(),
        action="Attack the sand creature",
    )
    dice = [
        DiceResultOut(
            notation="1d20",
            purpose="attack",
            natural=18,
            rolls=[18],
            modifier=0,
            total=18,
            dc=12,
            success=True,
        )
    ]
    out = GameplayService._mechanical_fallbacks(_state(), req, dice, [])
    assert not any(c.action == "apply_damage" for c in out)
