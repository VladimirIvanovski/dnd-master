from app.ai.dm_service import DMService
from app.ai.mock_provider import MockLLMProvider
from app.game.state import GameStateLoader
from app.schemas.gameplay import DMResponse, PlayerActionRequest, StateChange
from app.services.campaign import CampaignService, CharacterService
from app.services.gameplay import GameplayService
from app.schemas.common import CampaignCreate, CharacterCreate
from app.game.engine import GameEngine


def test_gameplay_service_with_mock_llm(db):
    campaign = CampaignService(db).create(CampaignCreate(name="C1", description="d"))
    character = CharacterService(db).create(
        CharacterCreate(campaign_id=campaign.id, name="Aria")
    )

    fixed = DMResponse(
        narration="Marta nods and hands you a rusty key.",
        dialogue=[{"speaker": "Marta", "text": "Keep this safe."}],
        events=[
            {
                "event_type": "ITEM_ACQUIRED",
                "summary": "Received a rusty key",
                "importance": 6,
            }
        ],
        state_changes=[
            StateChange(action="add_item", params={"name": "Rusty Key", "quantity": 1}),
            StateChange(action="gain_xp", params={"amount": 10}),
        ],
        memory_candidates=[
            {"content": "Marta gave Aria a rusty key.", "importance": 6}
        ],
    )
    service = GameplayService(
        db,
        dm=DMService(MockLLMProvider(fixed_response=fixed)),
        engine=GameEngine(db),
    )
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="Ask Marta for help",
        )
    )
    assert "rusty key" in result.narration.lower() or "Marta" in result.narration
    assert any("added item" in c for c in result.applied_changes)
    assert result.applied_events
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert any(i.name == "Rusty Key" for i in state.inventory)


def test_rejects_illegal_state_change(db):
    campaign = CampaignService(db).create(CampaignCreate(name="C2"))
    character = CharacterService(db).create(
        CharacterCreate(campaign_id=campaign.id, name="Borin")
    )
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="drop_table", params={})],
    )
    assert result.rejected
    assert not result.applied
