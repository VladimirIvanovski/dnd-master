from app.ai.dm_service import DMService
from app.ai.mock_provider import MockLLMProvider
from app.ai.quality import quality_violations, scrub_dice_prose
from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import DMResponse, PlayerActionRequest
from app.services.gameplay import GameplayService
from tests.conftest import start_campaign


def test_scrub_dice_prose():
    assert "rolled" not in scrub_dice_prose("You rolled a 7 and the door yields.").lower()
    assert quality_violations("You rolled a 12 vs DC 14") == ["dice-in-prose"]
    assert quality_violations("The door sticks.", secrets=["SECRET"]) == []
    assert "secret-leak" in quality_violations("The SECRET is out", secrets=["SECRET"])


def test_gameplay_strips_dice_quoted_by_dm(db):
    _user, campaign, character = start_campaign(db, username="dice_owner")
    speaker = "Guide"
    state = GameStateLoader(db).load(campaign.id, character.id)
    if state.nearby_npcs:
        speaker = state.nearby_npcs[0].name
    fixed = DMResponse(
        narration="You rolled a 7. The latch gives.",
        dialogue=[{"speaker": speaker, "text": "Natural 20, friend."}],
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
            action="Force the latch",
        )
    )
    blob = result.narration + " " + " ".join(d.text for d in result.dialogue)
    assert quality_violations(blob) == []
