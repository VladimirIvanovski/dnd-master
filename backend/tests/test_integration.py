"""Integration tests: memory, authority, dice gating, combat, persistence."""

from app.ai.dm_service import DMService
from app.ai.mock_provider import MockLLMProvider
from app.game.engine import GameEngine, MAX_GOLD_GAIN
from app.game.state import GameStateLoader
from app.schemas.common import CampaignCreate, CharacterCreate
from app.schemas.gameplay import DMResponse, PlayerActionRequest, StateChange
from app.services.campaign import CampaignService, CharacterService
from app.services.gameplay import GameplayService
from app.services.memory import MemoryService
from app.services.embedding import EmbeddingService
import random


def _start(db):
    campaign = CampaignService(db).create(CampaignCreate(name="Persist", description="t"))
    character = CharacterService(db).create(
        CharacterCreate(campaign_id=campaign.id, name="Hero")
    )
    return campaign, character


def test_authority_rejects_illegal_and_huge_gold(db):
    campaign, character = _start(db)
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="set_hp", params={"amount": 999}),
            StateChange(action="gain_gold", params={"amount": 1000}),
            StateChange(action="spend_gold", params={"amount": -5}),
        ],
    )
    assert not result.applied
    assert len(result.rejected) == 3
    # legal small gold still works
    ok = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="gain_gold", params={"amount": MAX_GOLD_GAIN})],
    )
    assert ok.applied


def test_dice_gate_blocks_failed_changes(db):
    campaign, character = _start(db)
    engine = GameEngine(db, rng=random.Random(1))
    fixed = DMResponse(
        narration="You attempt a desperate leap.",
        dice_requests=[{"kind": "d20", "notation": "1d20", "purpose": "Leap", "skill": "dexterity", "dc": 30}],
        state_changes=[
            StateChange(action="gain_xp", params={"amount": 50, "requires_success": True}),
            StateChange(action="add_item", params={"name": "Lucky Charm", "quantity": 1}),
        ],
        events=[{"event_type": "DISCOVERY_MADE", "summary": "Leap attempt"}],
    )
    service = GameplayService(db, dm=DMService(MockLLMProvider(fixed_response=fixed)), engine=engine)
    out = service.handle_action(
        PlayerActionRequest(campaign_id=campaign.id, character_id=character.id, action="Leap the chasm")
    )
    assert out.dice_results
    assert out.dice_results[0].success is False
    assert any("Lucky Charm" in c or "added item" in c for c in out.applied_changes)
    assert not any("xp=" in c for c in out.applied_changes)


def test_memory_elira_key_and_promise(db):
    campaign, character = _start(db)
    service = GameplayService(db)
    service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I approach and meet Elira",
        )
    )
    service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I promise to help Elira",
        )
    )
    service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I accept the silver key from Elira",
        )
    )
    # Simulate restart: new service, same DB
    resumed = GameplayService(db)
    key_ans = resumed.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="Who gave me the silver key?",
        )
    )
    assert "elira" in key_ans.narration.lower() or "key" in key_ans.narration.lower()
    promise = resumed.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="What did I promise Elira?",
        )
    )
    assert "promise" in promise.narration.lower() or "help" in promise.narration.lower()

    state = GameStateLoader(db).load(campaign.id, character.id)
    assert any(i.name == "Silver Key" for i in state.inventory)
    assert any(q.title == "Aid Elira" for q in state.active_quests)


def test_combat_initiative_damage_rewards(db):
    campaign, character = _start(db)
    engine = GameEngine(db, rng=random.Random(2))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {"name": "Hero", "combatant_type": "character", "hp": 12, "initiative": 15},
                        {"name": "Goblin", "combatant_type": "enemy", "hp": 7, "initiative": 8},
                    ]
                },
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat is not None
    goblin = next(c for c in state.combat.combatants if c.name == "Goblin")
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(goblin.id), "amount": 20},
            )
        ],
    )
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="advance_turn", params={}),
            StateChange(
                action="end_combat",
                params={"reward_xp": 40, "reward_gold": 10},
            ),
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat is None or state.combat.status == "ended"
    assert state.character.xp >= 40
    assert state.character.gold >= 25


def test_persistence_across_loader(db):
    campaign, character = _start(db)
    service = GameplayService(db)
    service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I accept the silver key from Elira",
        )
    )
    # New loader instance = "restart"
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.current_location is not None
    assert state.current_location.name
    assert any(i.name == "Silver Key" for i in state.inventory)
    mems = MemoryService(db, EmbeddingService()).retrieve(state, "silver key")
    assert any("key" in m.lower() for m in mems)


def test_api_ownership_and_state(client):
    created = client.post("/api/campaigns", json={"name": "Owned", "description": ""})
    assert created.status_code == 200
    campaign = created.json()
    ch = client.post(
        "/api/characters",
        json={"campaign_id": campaign["id"], "name": "A"},
        headers={"X-Username": "player"},
    )
    assert ch.status_code == 200
    character = ch.json()

    forbidden = client.get(
        f"/api/campaigns/{campaign['id']}",
        headers={"X-Username": "intruder"},
    )
    assert forbidden.status_code == 403

    chars = client.get(
        f"/api/characters?campaign_id={campaign['id']}",
        headers={"X-Username": "player"},
    )
    assert chars.status_code == 200
    assert len(chars.json()) >= 1

    state = client.get(
        f"/api/gameplay/state?campaign_id={campaign['id']}&character_id={character['id']}",
        headers={"X-Username": "player"},
    )
    assert state.status_code == 200
    body = state.json()
    assert body["current_location"]["name"]
    assert len(body["nearby_npcs"]) >= 1
    assert body["world_state"].get("tone")
    assert body["world_state"].get("opening_narration")
