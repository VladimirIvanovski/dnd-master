from app.game.engine import GameEngine
from app.schemas.gameplay import DialogueLine, StateChange
from app.services.gameplay import GameplayService
from app.game.state import GameStateLoader


def _start(db):
    from tests.conftest import start_campaign

    _user, campaign, character = start_campaign(db, username="baelor_owner")
    character.name = "Baelor"
    db.commit()
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


def test_dialogue_does_not_spawn_unknown_speakers(db):
    campaign, character = _start(db)
    engine = GameEngine(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    service = GameplayService(db, engine=engine)
    changes = service._dialogue_npcs_as_changes(
        state,
        [DialogueLine(speaker="Khalid", text="I'm Khalid.")],
    )
    assert changes == []
    before = {n.name for n in state.nearby_npcs}
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=changes,
    )
    refreshed = GameStateLoader(db).load(campaign.id, character.id)
    assert {n.name for n in refreshed.nearby_npcs} == before


from uuid import uuid4

from app.schemas.gameplay import DialogueLine, StateChange
from app.schemas.state import CharacterState, GameState
from app.services.gameplay import GameplayService


def test_no_auto_spawn_when_scene_empty():
    ch = CharacterState(
        id=uuid4(),
        name="Hero",
        race="Human",
        class_name="Fighter",
        level=1,
        xp=0,
        hp=10,
        max_hp=10,
        ac=12,
        gold=0,
        abilities={},
    )
    state = GameState(
        campaign_id=uuid4(),
        campaign_name="Test",
        character=ch,
        nearby_npcs=[],
    )
    changes = GameplayService._dialogue_npcs_as_changes(
        state,
        [DialogueLine(speaker="Ghost Stranger", text="Hello?")],
    )
    assert changes == []
