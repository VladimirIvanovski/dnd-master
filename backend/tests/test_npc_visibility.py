"""NPC visibility: only living NPCs at the player's current location."""

from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import StateChange
from tests.conftest import start_campaign


def test_dead_npc_not_in_nearby(db):
    _user, campaign, character = start_campaign(db, username="npc_vis_dead")
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.nearby_npcs
    victim = state.nearby_npcs[0]

    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="update_npc",
                params={"npc_id": str(victim.id), "is_alive": False},
            )
        ],
    )
    refreshed = GameStateLoader(db).load(campaign.id, character.id)
    assert all(n.id != victim.id for n in refreshed.nearby_npcs)
    assert all(n.is_alive for n in refreshed.nearby_npcs)


def test_npc_not_shown_after_player_leaves_location(db):
    _user, campaign, character = start_campaign(db, username="npc_vis_leave")
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.current_location and state.nearby_npcs
    old_names = {n.name for n in state.nearby_npcs}
    old_loc = state.current_location

    # Create a second location and move there
    from app.database.repositories import LocationRepository

    elsewhere = LocationRepository(db).create(
        campaign.id,
        name="Lonely Road",
        description="Empty dust and wind.",
        location_type="wilderness",
    )
    db.commit()

    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="move_to_location",
                params={"location_id": str(elsewhere.id)},
            )
        ],
    )
    refreshed = GameStateLoader(db).load(campaign.id, character.id)
    assert refreshed.current_location
    assert refreshed.current_location.id == elsewhere.id
    assert refreshed.current_location.id != old_loc.id
    # Original settlement NPCs should not appear on the lonely road
    assert not any(n.name in old_names for n in refreshed.nearby_npcs)


def test_combat_defeat_marks_npc_dead(db):
    _user, campaign, character = start_campaign(db, username="npc_vis_combat")
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    victim = state.nearby_npcs[0]

    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": character.name,
                            "combatant_type": "player",
                            "ref_id": str(character.id),
                            "hp": 20,
                            "ac": 14,
                        },
                        {
                            "name": victim.name,
                            "combatant_type": "enemy",
                            "ref_id": str(victim.id),
                            "hp": 5,
                            "ac": 10,
                        },
                    ]
                },
            )
        ],
    )
    session = engine.combat.active_for_campaign(campaign.id)
    assert session
    foe = next(c for c in session.combatants if c.name == victim.name)
    engine.damage_combatant(campaign.id, foe.id, 99)

    refreshed = GameStateLoader(db).load(campaign.id, character.id)
    assert all(n.id != victim.id for n in refreshed.nearby_npcs)
