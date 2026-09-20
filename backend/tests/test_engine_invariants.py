from app.database.repositories.character import InventoryRepository
from app.database.repositories.world import NPCRepository
from app.game.engine import GameEngine
from app.game.rules import carry_capacity
from app.game.state import GameStateLoader
from app.schemas.gameplay import StateChange
from tests.test_game_core import _seed


def test_temp_hp_absorbs_damage(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="set_temp_hp", params={"amount": 4})],
    )
    engine.apply_damage(character.id, 3)
    ch = engine.characters.get(character.id)
    assert ch.hp == 10
    assert ch.temp_hp == 1
    engine.apply_damage(character.id, 5)
    ch = engine.characters.get(character.id)
    assert ch.temp_hp == 0
    assert ch.hp == 6


def test_heal_does_not_exceed_max(db):
    _, _, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_damage(character.id, 2)
    engine.heal(character.id, 99)
    assert engine.characters.get(character.id).hp == 10


def test_xp_never_decreases_and_levels(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="gain_xp", params={"amount": -10})],
    )
    assert result.rejected
    engine.gain_xp(character.id, 300)
    ch = engine.characters.get(character.id)
    assert ch.level >= 2
    assert ch.xp >= 300


def test_spend_gold_requires_funds(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="spend_gold", params={"amount": 5})],
    )
    assert any("not enough gold" in r for r in result.rejected)
    assert engine.characters.get(character.id).gold == 0


def test_unique_item_does_not_duplicate(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.add_item(
        character.id, campaign.id, "Moonblade", item_type="weapon", properties={"unique": True}
    )
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="add_item",
                params={"name": "Moonblade", "item_type": "weapon", "unique": True},
            )
        ],
    )
    assert result.rejected
    rows = InventoryRepository(db).list_for_character(character.id)
    assert len(rows) == 1
    assert rows[0].quantity == 1


def test_consume_requires_possession_and_heals(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_damage(character.id, 5)
    link = engine.add_item(
        character.id,
        campaign.id,
        "Potion",
        item_type="consumable",
        properties={"heal": 4, "consumable": True},
    )
    missing = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="consume_item", params={"item_id": "00000000-0000-0000-0000-000000000001"})],
    )
    assert missing.rejected
    ok = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="consume_item", params={"item_id": str(link.item_id)})],
    )
    assert ok.applied
    assert engine.characters.get(character.id).hp == 9
    assert InventoryRepository(db).list_for_character(character.id) == []


def test_equip_without_item_fails_and_slots_are_unique(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    first = engine.add_item(character.id, campaign.id, "Iron Sword", item_type="weapon")
    second = engine.add_item(character.id, campaign.id, "Steel Sword", item_type="weapon")
    fake = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="equip_item", params={"item_id": "00000000-0000-0000-0000-000000000001"})],
    )
    assert fake.rejected
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="equip_item", params={"item_id": str(first.item_id)}),
            StateChange(action="equip_item", params={"item_id": str(second.item_id)}),
        ],
    )
    rows = {r.item.name: r.equipped for r in InventoryRepository(db).list_for_character(character.id)}
    assert rows["Steel Sword"] is True
    assert rows["Iron Sword"] is False


def test_armor_raises_ac(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    mail = engine.add_item(
        character.id,
        campaign.id,
        "Mail",
        item_type="armor",
        properties={"ac_bonus": 3},
    )
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="equip_item", params={"item_id": str(mail.item_id)})],
    )
    assert engine.characters.get(character.id).ac >= 13


def test_encumbrance_rejects_overload(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    cap = carry_capacity(character.strength)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="add_item",
                params={"name": "Anvil", "item_type": "misc", "weight": cap + 1},
            )
        ],
    )
    assert any("too heavy" in r for r in result.rejected)
    assert InventoryRepository(db).list_for_character(character.id) == []


def test_quest_complete_is_not_double_paid(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    start = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_quest",
                params={"title": "Rats", "objectives": ["Kill rats"], "reward_xp": 50, "reward_gold": 3},
            )
        ],
    )
    assert start.applied
    from app.database.repositories.world import QuestRepository

    qid = QuestRepository(db).active_for_campaign(campaign.id, character.id)[0].id
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="complete_quest", params={"quest_id": str(qid)})],
    )
    xp_after = engine.characters.get(character.id).xp
    gold_after = engine.characters.get(character.id).gold
    again = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="complete_quest", params={"quest_id": str(qid)})],
    )
    assert again.rejected
    ch = engine.characters.get(character.id)
    assert ch.xp == xp_after
    assert ch.gold == gold_after


def test_time_cannot_go_backwards(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="set_time", params={"value": "Day 2, Evening"})],
    )
    back = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="set_time", params={"value": "Day 1, Morning"})],
    )
    assert back.rejected
    assert engine.campaigns.get(campaign.id).current_time == "Day 2, Evening"


def test_dead_npc_not_nearby_and_cannot_move(db):
    _, campaign, loc, character = _seed(db)
    engine = GameEngine(db)
    npc = NPCRepository(db).create(campaign.id, name="Edrik", location_id=loc.id)
    other = NPCRepository(db).create(campaign.id, name="Camp", location_id=loc.id)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="update_npc",
                params={"npc_id": str(npc.id), "is_alive": False, "hp": 0},
            )
        ],
    )
    nearby = NPCRepository(db).nearby(loc.id)
    assert all(n.name != "Edrik" for n in nearby)
    moved = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="update_npc",
                params={"npc_id": str(npc.id), "location_id": str(other.id)},
            )
        ],
    )
    # other.id is an npc id, not location — invalid or dead move
    assert moved.rejected
    dead_move = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="update_npc",
                params={"npc_id": str(npc.id), "location_id": str(loc.id)},
            )
        ],
    )
    assert any("dead npc" in r for r in dead_move.rejected)


def test_second_combat_rejected(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    combatants = [
        {"name": "Hero", "combatant_type": "player", "hp": 10, "ac": 10, "ref_id": str(character.id)},
        {"name": "Wolf", "combatant_type": "enemy", "hp": 6, "ac": 11},
    ]
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="start_combat", params={"combatants": combatants})],
    )
    again = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="start_combat", params={"combatants": combatants})],
    )
    assert again.rejected


def test_rest_advances_time_and_heals(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_damage(character.id, 4)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="rest", params={})],
    )
    ch = engine.characters.get(character.id)
    assert ch.hp > 6
    assert engine.campaigns.get(campaign.id).current_time != "Day 1, Morning"


def test_buy_requires_gold_then_owns_item(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    poor = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="buy_item", params={"name": "Rations", "price": 5, "item_type": "food"})],
    )
    assert poor.rejected
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="gain_gold", params={"amount": 8})],
    )
    bought = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="buy_item", params={"name": "Rations", "price": 5, "item_type": "food"})],
    )
    assert bought.applied
    ch = engine.characters.get(character.id)
    assert ch.gold == 3
    rows = InventoryRepository(db).list_for_character(character.id)
    assert any(r.item.name == "Rations" for r in rows)


def test_sell_requires_item(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    missing = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="sell_item", params={"item_id": "00000000-0000-0000-0000-000000000001", "price": 2})],
    )
    assert missing.rejected
    link = engine.add_item(character.id, campaign.id, "Junk", item_type="misc")
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="sell_item", params={"item_id": str(link.item_id), "price": 2})],
    )
    assert engine.characters.get(character.id).gold == 2
    assert InventoryRepository(db).list_for_character(character.id) == []


def test_locked_location_blocks_travel(db):
    _, campaign, loc, character = _seed(db)
    from app.database.models import Location
    from app.utils.ids import utcnow
    import uuid

    vault = Location(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        name="Vault",
        description="A door",
        extra={"locked": True, "unlocked": False},
        created_at=utcnow(),
    )
    db.add(vault)
    db.flush()
    engine = GameEngine(db)
    blocked = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    assert any("locked" in r for r in blocked.rejected)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="unlock_location", params={"location_id": str(vault.id)})],
    )
    ok = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    assert ok.applied
    assert engine.characters.get(character.id).location_id == vault.id


def test_flee_ends_combat_without_xp(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    combatants = [
        {"name": "Hero", "combatant_type": "player", "hp": 10, "ac": 10, "ref_id": str(character.id)},
        {"name": "Wolf", "combatant_type": "enemy", "hp": 6, "ac": 11},
    ]
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="start_combat", params={"combatants": combatants})],
    )
    xp_before = engine.characters.get(character.id).xp
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="flee_combat", params={})],
    )
    assert engine.combat.active_for_campaign(campaign.id) is None
    assert engine.characters.get(character.id).xp == xp_before


def test_hp_zero_sets_unconscious(db):
    _, _, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_damage(character.id, 99)
    ch = engine.characters.get(character.id)
    assert ch.hp == 0
    assert "unconscious" in (ch.extra or {}).get("conditions", [])


def test_weapon_add_item_needs_a_source(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    conjured = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="add_item",
                params={"name": "Legendary Sword", "item_type": "weapon"},
            )
        ],
    )
    assert any("cannot conjure" in r for r in conjured.rejected)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="spawn_npc",
                params={"name": "Elira", "title": "guide", "personality": "kind"},
            )
        ],
    )
    gifted = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="add_item",
                params={
                    "name": "Hunting Knife",
                    "item_type": "weapon",
                    "source": "gift",
                },
            )
        ],
    )
    assert gifted.applied
    rows = InventoryRepository(db).list_for_character(character.id)
    assert any(r.item.name == "Hunting Knife" for r in rows)


def test_exhausted_penalizes_checks_and_travel(db):
    from app.database.models import Location
    from app.game.rules import extra_with_conditions, vitals_from_extra
    from app.schemas.gameplay import DiceRequest
    import random

    _, campaign, loc, character = _seed(db)
    vault = Location(
        campaign_id=campaign.id,
        name="Vault",
        description="Stone",
        location_type="dungeon",
    )
    db.add(vault)
    db.flush()
    engine = GameEngine(db, rng=random.Random(1))
    ch = engine.characters.get(character.id)
    ch.extra = extra_with_conditions(
        {"hunger": 10, "thirst": 0, "stamina": 5}, ["exhausted"]
    )
    db.flush()
    rolls = engine.resolve_dice_requests(
        character.id, [DiceRequest(kind="d20", skill="athletics", dc=1)]
    )
    assert rolls[0].modifier == -2
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    after = vitals_from_extra(engine.characters.get(character.id).extra)
    assert after["hunger"] == 14
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="rest", params={})],
    )
    names = (engine.characters.get(character.id).extra or {}).get("conditions", [])
    assert "exhausted" not in names


def test_silver_and_copper_spend(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="gain_silver", params={"amount": 4}),
            StateChange(action="gain_copper", params={"amount": 6}),
        ],
    )
    ch = engine.characters.get(character.id)
    assert ch.silver == 4 and ch.copper == 6
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="spend_silver", params={"amount": 1}),
            StateChange(action="spend_copper", params={"amount": 2}),
        ],
    )
    ch = engine.characters.get(character.id)
    assert ch.silver == 3 and ch.copper == 4
    broke = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="spend_silver", params={"amount": 99})],
    )
    assert any("not enough silver" in r for r in broke.rejected)


def test_weapon_breaks_after_durability_runs_out(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    link = engine.add_item(
        character.id,
        campaign.id,
        "Hatchet",
        item_type="weapon",
        properties={"max_durability": 1},
    )
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="equip_item", params={"item_id": str(link.item_id)})],
    )
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
                            "initiative": 1,
                            "x": 3,
                            "y": 2,
                        },
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 20,
                            "ref_id": str(character.id),
                            "x": 3,
                            "y": 1,
                        },
                    ]
                },
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    wolf = next(c for c in state.combat.combatants if c.name == "Wolf")
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="damage_combatant",
                params={"combatant_id": str(wolf.id), "amount": 1},
            )
        ],
    )
    row = InventoryRepository(db).list_for_character(character.id)[0]
    assert row.durability == 0
    assert row.equipped is False
    again = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="equip_item", params={"item_id": str(link.item_id)})],
    )
    assert any("broken" in r for r in again.rejected)


def test_storm_taxes_travel_and_checks(db):
    from app.database.models import Location
    from app.game.rules import vitals_from_extra
    from app.schemas.gameplay import DiceRequest
    import random

    _, campaign, _, character = _seed(db)
    vault = Location(
        campaign_id=campaign.id, name="Ridge", description="Wind", location_type="wilds"
    )
    db.add(vault)
    db.flush()
    engine = GameEngine(db, rng=random.Random(1))
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="set_weather", params={"value": "Storm"})],
    )
    rolls = engine.resolve_dice_requests(
        character.id, [DiceRequest(kind="d20", skill="athletics", dc=1)]
    )
    assert rolls[0].modifier == -1
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="move_to_location", params={"location_id": str(vault.id)})],
    )
    after = vitals_from_extra(engine.characters.get(character.id).extra)
    assert after["hunger"] == 8


def test_checkpoint_restores_hp_and_inventory(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.add_item(character.id, campaign.id, "Torch", item_type="misc")
    engine.apply_damage(character.id, 3)
    saved = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="save_checkpoint", params={"name": "camp"})],
    )
    assert saved.applied
    engine.heal(character.id, 99)
    engine.add_item(character.id, campaign.id, "Pebble", item_type="misc")
    loaded = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="load_checkpoint", params={"name": "camp"})],
    )
    assert loaded.applied
    ch = engine.characters.get(character.id)
    assert ch.hp == 7
    names = [r.item.name for r in InventoryRepository(db).list_for_character(character.id)]
    assert names == ["Torch"]
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert "camp" in state.checkpoints
    assert "checkpoints" not in state.world_state
