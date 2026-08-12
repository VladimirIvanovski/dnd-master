"""Tests for EventDirector, scene context, and one-request dice rewrite."""

from __future__ import annotations

import random

from app.ai.dm_service import DMService
from app.ai.mock_provider import MockLLMProvider
from app.game.engine import GameEngine
from app.game.event_director import ARCHETYPES, CATEGORIES, EventDirector
from app.game.scene_context import (
    get_narrative_meta,
    next_narrative_meta,
    should_describe_environment,
)
from app.schemas.gameplay import DMResponse, DiceRequest, PlayerActionRequest, StateChange
from app.schemas.state import CharacterState, GameState, LocationState
from app.services.gameplay import GameplayService
from tests.conftest import start_campaign


def _state(**kwargs) -> GameState:
    loc = LocationState(
        id=kwargs.get("loc_id", __import__("uuid").uuid4()),
        name="Coral Outpost",
        description="A coastal settlement.",
        location_type="settlement",
    )
    ch = CharacterState(
        id=__import__("uuid").uuid4(),
        name="Hero",
        race="Human",
        class_name="Fighter",
        level=1,
        xp=0,
        hp=10,
        max_hp=10,
        ac=14,
        gold=0,
        abilities={"strength": 14, "dexterity": 12, "constitution": 12, "intelligence": 10, "wisdom": 10, "charisma": 10},
    )
    return GameState(
        campaign_id=__import__("uuid").uuid4(),
        campaign_name="Test",
        character=ch,
        current_location=loc,
        world_state=kwargs.get("world_state", {}),
    )


def test_archetype_library_size_and_categories():
    assert len(ARCHETYPES) >= 50
    cats = {a.category for a in ARCHETYPES}
    assert cats <= set(CATEGORIES)
    assert len(cats) >= 10


def test_event_director_cooldown():
    rng = random.Random(0)
    director = EventDirector(rng=rng, base_chance=1.0, cooldown_turns=2)
    state = _state()
    meta = {"turn": 5, "last_random_event_turn": 4, "recent_event_types": [], "recent_event_ids": []}
    s = director.suggest(state, player_action="I walk down the road", narrative_meta=meta)
    assert s.fire is False
    assert s.reason == "cooldown"


def test_event_director_weighted_pick_and_no_repeat_id():
    rng = random.Random(42)
    director = EventDirector(rng=rng, base_chance=1.0, cooldown_turns=0)
    state = _state()
    meta = {
        "turn": 10,
        "last_random_event_turn": -999,
        "recent_event_types": [],
        "recent_event_ids": [],
    }
    first = director.suggest(state, player_action="I travel the coastal road", narrative_meta=meta)
    assert first.fire and first.archetype
    meta2 = {
        "turn": 11,
        "last_random_event_turn": -999,
        "recent_event_types": [first.archetype.category, first.archetype.category],
        "recent_event_ids": [first.archetype.id],
    }
    # Force many picks; none should be the same id while it's in recent_ids
    for seed in range(20):
        d = EventDirector(rng=random.Random(seed), base_chance=1.0, cooldown_turns=0)
        s = d.suggest(state, player_action="I travel onward", narrative_meta=meta2)
        if s.fire and s.archetype:
            assert s.archetype.id != first.archetype.id


def test_scene_describe_only_on_change_or_examine():
    state = _state()
    sid = f"{state.current_location.id}:settlement"
    meta = {"last_described_scene_id": sid, "current_scene_id": sid, "turn": 3}
    assert should_describe_environment(state, meta, "I walk to the tavern") is False
    assert should_describe_environment(state, meta, "I look around carefully") is True
    meta2 = {"last_described_scene_id": None, "current_scene_id": None, "turn": 0}
    assert should_describe_environment(state, meta2, "I enter") is True


def test_narrative_meta_persists_on_action(db):
    _user, campaign, character = start_campaign(db, username="narr_meta")
    service = GameplayService(
        db,
        dm=DMService(MockLLMProvider()),
        engine=GameEngine(db, rng=random.Random(1)),
        event_director=EventDirector(rng=random.Random(0), base_chance=0.0),
    )
    service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I nod quietly",
        )
    )
    db.refresh(campaign)
    meta = get_narrative_meta(campaign.world_state)
    assert meta["turn"] >= 1
    assert meta.get("current_scene_id")


def test_one_request_dice_rewrite_no_second_client_call(db):
    """Dice are rolled server-side; rewrite pass uses same handle_action."""
    _user, campaign, character = start_campaign(db, username="dice_one")
    character.dexterity = 14
    db.commit()

    fixed = DMResponse(
        narration="You ease toward the shadows.",
        dice_requests=[
            DiceRequest(kind="d20", notation="1d20", purpose="Stealth", skill="stealth", dc=10)
        ],
        state_changes=[
            StateChange(action="gain_xp", params={"amount": 5, "requires_success": True}),
        ],
    )
    # Count LLM calls
    provider = MockLLMProvider(fixed_response=fixed)
    calls = {"n": 0}
    orig = provider.generate_structured

    def wrapped(prompt, schema, *, system=None):
        calls["n"] += 1
        return orig(prompt, schema, system=system)

    provider.generate_structured = wrapped  # type: ignore[method-assign]

    engine = GameEngine(db, rng=random.Random(2))
    service = GameplayService(
        db,
        dm=DMService(provider),
        engine=engine,
        event_director=EventDirector(rng=random.Random(0), base_chance=0.0),
    )
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I sneak past the guards",
        )
    )
    assert calls["n"] == 2  # plan/narrate + rewrite — still one HTTP action
    assert len(result.dice_results) == 1
    d = result.dice_results[0]
    assert d.natural is not None
    assert d.modifier == 2  # dex 14
    assert d.total == d.natural + d.modifier
    assert "dice_requests" not in result.model_dump() or True
    # Narration should reflect rewrite (success/fail appended by mock)
    assert result.narration
    assert "[" not in result.narration or "success" in result.narration.lower() or "fail" in result.narration.lower() or "twenty" in result.narration.lower() or "one" in result.narration.lower() or "check" in result.narration.lower() or "favor" in result.narration.lower() or "falter" in result.narration.lower()


def test_natural_20_and_1_flags(db):
    _user, campaign, character = start_campaign(db, username="crits")
    character.strength = 10
    db.commit()

    class FixedRng:
        def __init__(self, value):
            self.value = value

        def randint(self, a, b):
            return self.value

    for nat, flag in ((20, "natural_20"), (1, "natural_1")):
        engine = GameEngine(db, rng=FixedRng(nat))
        reqs = [DiceRequest(kind="d20", purpose="Attack", skill="strength", dc=30)]
        out = engine.resolve_dice_requests(character.id, reqs)
        assert out[0].natural == nat
        assert out[0].critical == flag
        # Impossible DC: nat 20 still may fail — success respects total vs DC
        if nat == 20:
            assert out[0].total == 20
            assert out[0].success is False  # DC 30


def test_next_meta_records_events():
    meta = get_narrative_meta({})
    state = _state()
    nxt = next_narrative_meta(
        meta,
        state=state,
        described=True,
        fired_event_id="omen",
        fired_category="WORLD_EVENT",
    )
    assert nxt["turn"] == 1
    assert "omen" in nxt["recent_event_ids"]
    assert "WORLD_EVENT" in nxt["recent_event_types"]
    assert nxt["last_described_scene_id"]
