from app.game.engine import GameEngine
from app.schemas.common import CampaignCreate, CharacterCreate
from app.schemas.gameplay import DialogueLine, StateChange
from app.services.campaign import CampaignService, CharacterService
from app.services.gameplay import GameplayService
from app.game.state import GameStateLoader


def _start(db):
    campaign = CampaignService(db).create(CampaignCreate(name="NPC Item Fix", description="t"))
    character = CharacterService(db).create(
        CharacterCreate(campaign_id=campaign.id, name="Baelor")
    )
    return campaign, character


def test_add_item_accepts_alternate_keys(db):
    campaign, character = _start(db)
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(action="add_item", params={"item_name": "Rough Stone", "quantity": 1}),
        ],
    )
    assert any("Rough Stone" in c for c in result.applied)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert any(i.name == "Rough Stone" for i in state.inventory)


def test_spawn_npc_and_dialogue_speakers(db):
    campaign, character = _start(db)
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    service = GameplayService(db, engine=engine)
    changes = service._dialogue_npcs_as_changes(
        state,
        [DialogueLine(speaker="Khalid", text="I'm Khalid.")],
    )
    assert changes and changes[0].action == "spawn_npc"
    applied = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=changes,
    )
    assert any("Khalid" in c for c in applied.applied)
    refreshed = GameStateLoader(db).load(campaign.id, character.id)
    assert any(n.name == "Khalid" for n in refreshed.nearby_npcs)
