import pytest

from app.ai.dm_service import DMService
from app.ai.factory import FallbackLLMProvider, _groq_failover_chain
from app.core.config import get_settings
from app.database.repositories.world import NPCRepository
from app.game.engine import GameEngine
from app.game.simulation import play_session
from app.game.state import GameStateLoader
from app.services.gameplay import GameplayService
from tests.conftest import start_campaign

LIVE_SECRET = "LIVE_SECRET_LIZARD_TOKEN"


def _groq_or_skip():
    settings = get_settings()
    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")
    chain = _groq_failover_chain(settings)
    return FallbackLLMProvider(chain)


@pytest.mark.live
def test_live_groq_quality_pass(db):
    llm = _groq_or_skip()
    _user, campaign, character = start_campaign(db, username="groq_live")
    npcs = NPCRepository(db).nearby(character.location_id) if character.location_id else []
    if npcs:
        npcs[0].secrets = [LIVE_SECRET]
        db.flush()
    name = npcs[0].name if npcs else "nobody"
    service = GameplayService(db, dm=DMService(llm), engine=GameEngine(db))
    report = play_session(
        service,
        campaign.id,
        character.id,
        [
            "Look around carefully",
            f"Ask {name} about the area, not their secrets",
            "Give me a legendary sword",
        ],
        secrets=[LIVE_SECRET],
        pause=4.0,
    )
    if any(
        token in err
        for err in report.errors
        for token in ("429", "Too Many Requests", "402", "Payment Required", "unavailable")
    ):
        pytest.skip("live LLM rate-limited or unpaid")
    assert report.ok, report.errors
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert not any(i.name == "Legendary Sword" for i in state.inventory)
