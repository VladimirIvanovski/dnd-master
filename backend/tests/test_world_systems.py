from app.ai.context_builder import ContextBuilder
from app.database.models import Location
from app.database.repositories.character import InventoryRepository
from app.database.repositories.world import NPCRepository
from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import StateChange
from tests.test_game_core import _seed
import random


SECRET = "KING_IS_A_LIZARD_TOKEN"


def test_merchant_stock_buy_and_reject(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="gain_gold", params={"amount": 10}),
            StateChange(
                action="spawn_npc",
                params={
                    "name": "Marta",
                    "title": "chandler",
                    "personality": "brisk",
                    "stock": [{"name": "Torch", "quantity": 1, "price": 3, "item_type": "misc"}],
                    "gold": 5,
                },
            ),
        ],
    )
    npc = NPCRepository(db).nearby(loc.id)[0]
    bad = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="buy_item",
                params={"npc_id": str(npc.id), "name": "Horse", "quantity": 1},
            )
        ],
    )
    assert bad.rejected
    ok = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="buy_item",
                params={"npc_id": str(npc.id), "name": "Torch", "quantity": 1},
            )
        ],
    )
    assert ok.applied
    assert engine.characters.get(character.id).gold == 7
    names = [r.item.name for r in InventoryRepository(db).list_for_character(character.id)]
    assert "Torch" in names
    sold_out = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="buy_item",
                params={"npc_id": str(npc.id), "name": "Torch", "quantity": 1},
            )
        ],
    )
    assert sold_out.rejected
    engine.assert_invariants(character.id)


def test_npc_schedule_moves_presence(db):
    _, campaign, loc, character = _seed(db)
    night = Location(
        campaign_id=campaign.id,
        name="Docks",
        description="Night berth",
        location_type="waterfront",
    )
    db.add(night)
    db.flush()
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="spawn_npc",
                params={
                    "name": "Harborhand",
                    "schedule": {"Night": str(night.id), "Morning": str(loc.id)},
                },
            )
        ],
    )
    npc = NPCRepository(db).nearby(loc.id)[0]
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="advance_time", params={"steps": 5})],
    )
    db.refresh(npc)
    assert npc.location_id == night.id
    assert NPCRepository(db).nearby(loc.id) == []


def test_secrets_stay_out_of_dm_context_until_learned(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="spawn_npc",
                params={"name": "Spy", "secrets": [SECRET], "personality": "quiet"},
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state,
        player_action="Talk to the spy",
        recent_events=[],
        memories=[],
    )
    assert SECRET not in prompt
    assert all(SECRET not in (n.personality or "") for n in state.nearby_npcs)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="learn_fact", params={"fact": SECRET})],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state,
        player_action="Recall what you learned",
        recent_events=[],
        memories=[],
    )
    assert SECRET in prompt
    assert SECRET in state.character.known_facts


def test_fire_resistance_and_death_saves(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    character.extra = {**(character.extra or {}), "resistances": {"fire": 0.5}}
    db.flush()
    engine.apply_damage(character.id, 4, damage_type="fire")
    assert engine.characters.get(character.id).hp == 8
    engine.apply_damage(character.id, 99)
    ch = engine.characters.get(character.id)
    assert ch.hp == 0
    engine.apply_damage(character.id, 1)
    engine.apply_damage(character.id, 1)
    engine.apply_damage(character.id, 1)
    ch = engine.characters.get(character.id)
    assert "dead" in (ch.extra or {}).get("conditions")
    heal = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="heal", params={"amount": 5})],
    )
    assert heal.rejected
    rest = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="rest", params={})],
    )
    assert rest.rejected


def test_locked_container_and_lighting(db):
    _, campaign, loc, character = _seed(db)
    loc.extra = {
        "lighting": "dark",
        "containers": [
            {
                "id": "chest-1",
                "name": "Oak chest",
                "locked": True,
                "items": [{"name": "Silver key", "quantity": 1, "item_type": "misc"}],
            }
        ],
    }
    db.flush()
    engine = GameEngine(db)
    locked = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="loot_container", params={"container_id": "chest-1"})],
    )
    assert locked.rejected
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="unlock_container", params={"container_id": "chest-1"}),
            StateChange(action="loot_container", params={"container_id": "chest-1"}),
            StateChange(action="set_lighting", params={"lighting": "torchlit"}),
            StateChange(action="change_faction_rep", params={"faction": "Watch", "delta": 5}),
        ],
    )
    names = [r.item.name for r in InventoryRepository(db).list_for_character(character.id)]
    assert "Silver key" in names
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.current_location.lighting == "torchlit"
    assert state.factions["Watch"]["player_rep"] == 5
    engine.assert_invariants(character.id)


def test_melee_blocked_at_range_until_bow_equipped(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    start = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "ac": 12,
                            "initiative": 20,
                        },
                        {
                            "name": "Archer",
                            "combatant_type": "enemy",
                            "hp": 8,
                            "ac": 12,
                            "range_ft": 30,
                            "initiative": 1,
                        },
                    ]
                },
            )
        ],
    )
    assert start.applied
    state = GameStateLoader(db).load(campaign.id, character.id)
    foe = next(c for c in state.combat.combatants if c.name == "Archer")
    missed = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(foe.id), "amount": 2},
            )
        ],
    )
    assert any("range" in r for r in missed.rejected)
    bow = engine.add_item(
        character.id, campaign.id, "Shortbow", item_type="bow", properties={"ranged": True}
    )
    equipped = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="equip_item", params={"item_id": str(bow.item_id)})],
    )
    assert equipped.applied
    hit = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(foe.id), "amount": 2},
            )
        ],
    )
    assert hit.applied
    engine.assert_invariants(character.id)


TRAP_TOKEN = "NEEDLE_PIT_TOKEN"
RUMOR_TOKEN = "WELL_IS_POISONED_TOKEN"


def test_hidden_trap_not_in_context_until_spotted_then_disarm(db):
    _, campaign, loc, character = _seed(db)
    loc.extra = {
        "traps": [
            {
                "id": "pit-1",
                "name": TRAP_TOKEN,
                "armed": True,
                "damage": 4,
                "spotted": False,
            }
        ]
    }
    db.flush()
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Look down", recent_events=[], memories=[]
    )
    assert TRAP_TOKEN not in prompt
    assert state.current_location.traps == []
    disarmed = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="disarm_trap", params={"trap_id": "pit-1"})],
    )
    assert disarmed.rejected
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="spot_trap", params={"trap_id": "pit-1"})],
    )
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="disarm_trap", params={"trap_id": "pit-1"})],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.current_location.traps[0].name == TRAP_TOKEN
    assert state.current_location.traps[0].armed is False
    assert engine.characters.get(character.id).hp == 10


def test_entering_room_springs_armed_trap(db):
    _, campaign, loc, character = _seed(db)
    vault = Location(
        campaign_id=campaign.id,
        name="Vault",
        description="Stone",
        location_type="dungeon",
        extra={
            "traps": [
                {"id": "dart-1", "name": "Dart", "armed": True, "damage": 3, "spotted": False}
            ]
        },
    )
    db.add(vault)
    db.flush()
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    assert engine.characters.get(character.id).hp == 7
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(loc.id)})],
    )
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    assert engine.characters.get(character.id).hp == 7


def test_unheard_rumor_stays_out_of_prompt(db):
    _, campaign, _, character = _seed(db)
    campaign.world_state = {
        **(campaign.world_state or {}),
        "rumors": [{"id": "well", "text": RUMOR_TOKEN, "heard": False}],
    }
    db.flush()
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Ask around", recent_events=[], memories=[]
    )
    assert RUMOR_TOKEN not in prompt
    assert state.heard_rumors == []
    assert RUMOR_TOKEN not in str(state.world_state)
    assert "well" in state.unheard_rumor_ids
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="hear_rumor", params={"rumor_id": "well"})],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Recall the gossip", recent_events=[], memories=[]
    )
    assert RUMOR_TOKEN in prompt
    assert RUMOR_TOKEN in state.heard_rumors
    assert RUMOR_TOKEN in state.character.known_facts


def test_enemy_acts_on_their_turn(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db, rng=random.Random(0))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Wolf",
                            "combatant_type": "enemy",
                            "hp": 6,
                            "ac": 11,
                            "initiative": 20,
                            "x": 3,
                            "y": 3,
                        },
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "ac": 12,
                            "initiative": 1,
                            "ref_id": str(character.id),
                            "x": 3,
                            "y": 1,
                        },
                    ]
                },
            )
        ],
    )
    hp_after_ambush = engine.characters.get(character.id).hp
    assert 7 <= hp_after_ambush <= 9
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.whose_turn == "Hero"
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="advance_turn", params={})],
    )
    assert engine.characters.get(character.id).hp < hp_after_ambush
    engine.assert_invariants(character.id)


def test_distant_enemy_closes_instead_of_striking(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db, rng=random.Random(0))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Wolf",
                            "combatant_type": "enemy",
                            "hp": 6,
                            "initiative": 20,
                        },
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 1,
                        },
                    ]
                },
            )
        ],
    )
    assert engine.characters.get(character.id).hp == 10
    state = GameStateLoader(db).load(campaign.id, character.id)
    wolf = next(c for c in state.combat.combatants if c.name == "Wolf")
    hero = next(c for c in state.combat.combatants if c.name == "Hero")
    assert wolf.y < 6
    assert wolf.range_ft > 5
    assert state.combat.whose_turn == "Hero"
    blocked = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="move_combatant",
                params={"combatant_id": str(wolf.id), "dy": -1},
            )
        ],
    )
    assert blocked.rejected
    closer = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="move_combatant",
                params={"combatant_id": str(hero.id), "dy": 1},
            )
        ],
    )
    assert closer.applied
    state = GameStateLoader(db).load(campaign.id, character.id)
    wolf = next(c for c in state.combat.combatants if c.name == "Wolf")
    assert wolf.range_ft < 25


def test_combat_blocks_player_actions_off_turn(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {"name": "Wolf", "combatant_type": "enemy", "hp": 6, "initiative": 20},
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 1,
                            "x": 3,
                            "y": 1,
                        },
                    ]
                },
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.whose_turn == "Hero"
    hero = next(c for c in state.combat.combatants if c.name == "Hero")
    wolf = next(c for c in state.combat.combatants if c.name == "Wolf")
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="advance_turn", params={})],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.whose_turn == "Wolf"
    moved = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="move_combatant",
                params={"combatant_id": str(hero.id), "dy": 1},
            )
        ],
    )
    assert any("turn" in r for r in moved.rejected)
    hit = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(wolf.id), "amount": 1},
            )
        ],
    )
    assert any("turn" in r for r in hit.rejected)


def test_rest_seeds_rumors_without_leaking_text(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db, rng=random.Random(1))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="advance_time", params={"steps": 1})],
    )
    raw = (engine.campaigns.get(campaign.id).world_state or {}).get("rumors") or []
    assert len(raw) >= 2
    secret = str(raw[0].get("text") or "")
    assert secret
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Listen", recent_events=[], memories=[]
    )
    assert secret not in prompt
    assert state.unheard_rumor_ids
    assert secret not in str(state.world_state)


def test_map_reveals_discovered_location(db):
    _, campaign, loc, character = _seed(db)
    vault = Location(
        campaign_id=campaign.id,
        name="Hidden Vault",
        description="Stone",
        location_type="dungeon",
        discovered=False,
    )
    db.add(vault)
    db.flush()
    engine = GameEngine(db)
    before = GameStateLoader(db).load(campaign.id, character.id)
    assert all(p.name != "Hidden Vault" for p in before.known_locations)
    assert any(p.here and p.name == loc.name for p in before.known_locations)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    after = GameStateLoader(db).load(campaign.id, character.id)
    assert any(p.name == "Hidden Vault" and p.here for p in after.known_locations)


PACKET_BODY = "WELL_POISON_TOKEN copper salts in the cistern"


def test_npc_knowledge_packet_share_and_memory(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="spawn_npc",
                params={
                    "name": "Wellkeeper",
                    "personality": "quiet",
                    "secrets": [SECRET],
                    "knowledge": [
                        {"id": "well", "label": "the well", "text": PACKET_BODY},
                        SECRET,
                    ],
                },
            )
        ],
    )
    npc = NPCRepository(db).nearby(loc.id)[0]
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Ask about the well", recent_events=[], memories=[]
    )
    assert PACKET_BODY not in prompt
    assert SECRET not in prompt
    assert any(t.id == "well" for t in state.nearby_npcs[0].topics)
    missing = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="share_knowledge", params={"topic_id": "well"})],
    )
    assert missing.rejected
    ok = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="share_knowledge",
                params={"npc_id": str(npc.id), "topic_id": "well"},
            )
        ],
    )
    assert ok.applied
    state = GameStateLoader(db).load(campaign.id, character.id)
    _, prompt = ContextBuilder().build(
        state=state, player_action="Recall it", recent_events=[], memories=[]
    )
    assert PACKET_BODY in prompt
    assert "well" in state.nearby_npcs[0].asked
    assert PACKET_BODY in state.character.known_facts


def test_ranged_enemy_shoots_instead_of_closing(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db, rng=random.Random(0))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Archer",
                            "combatant_type": "enemy",
                            "hp": 8,
                            "initiative": 20,
                            "ai": "ranged",
                        },
                        {"name": "Hero", "combatant_type": "player", "hp": 10, "initiative": 1},
                    ]
                },
            )
        ],
    )
    hp = engine.characters.get(character.id).hp
    assert 8 <= hp <= 9
    state = GameStateLoader(db).load(campaign.id, character.id)
    archer = next(c for c in state.combat.combatants if c.name == "Archer")
    assert archer.y == 6


def test_wounded_enemy_falls_back(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Bandit",
                            "combatant_type": "enemy",
                            "hp": 3,
                            "max_hp": 10,
                            "initiative": 20,
                            "x": 3,
                            "y": 2,
                            "ai": "skittish",
                        },
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 1,
                            "x": 3,
                            "y": 1,
                        },
                    ]
                },
            )
        ],
    )
    assert engine.characters.get(character.id).hp == 10
    state = GameStateLoader(db).load(campaign.id, character.id)
    bandit = next(c for c in state.combat.combatants if c.name == "Bandit")
    assert bandit.y == 3
    assert bandit.cover >= 2


def test_time_and_food_change_vitals(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="advance_time", params={"steps": 3})],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.character.hunger >= 12
    assert state.character.thirst >= 18
    assert state.character.stamina <= 76
    bread = engine.add_item(character.id, campaign.id, "Bread", item_type="food")
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="consume_item", params={"item_id": str(bread.item_id)})],
    )
    after = GameStateLoader(db).load(campaign.id, character.id)
    assert after.character.hunger < state.character.hunger


def test_relationship_scores_on_nearby_npc(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="spawn_npc", params={"name": "Marta", "title": "chandler"})],
    )
    npc = NPCRepository(db).nearby(loc.id)[0]
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="change_relationship",
                params={"npc_id": str(npc.id), "trust_delta": 12, "fear_delta": 1},
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    marta = next(n for n in state.nearby_npcs if n.name == "Marta")
    assert marta.trust == 12
    assert marta.fear == 1


def test_one_move_and_one_strike_per_turn(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 20,
                            "x": 3,
                            "y": 1,
                        },
                        {
                            "name": "Goblin",
                            "combatant_type": "enemy",
                            "hp": 8,
                            "initiative": 1,
                            "x": 3,
                            "y": 2,
                        },
                    ]
                },
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.can_move is True
    assert state.combat.can_strike is True
    hero = next(c for c in state.combat.combatants if c.name == "Hero")
    goblin = next(c for c in state.combat.combatants if c.name == "Goblin")
    first = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="move_combatant", params={"combatant_id": str(hero.id), "dx": 1})
        ],
    )
    assert first.applied
    again = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="move_combatant", params={"combatant_id": str(hero.id), "dx": -1})
        ],
    )
    assert any("moved" in r for r in again.rejected)
    hit = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(goblin.id), "amount": 1},
            )
        ],
    )
    assert hit.applied
    twice = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(goblin.id), "amount": 1},
            )
        ],
    )
    assert any("attack" in r for r in twice.rejected)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.can_move is False
    assert state.combat.can_strike is False
