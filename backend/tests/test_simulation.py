from app.game.simulation import play_session, simulate_session
from app.game.state import GameStateLoader
from app.services.gameplay import GameplayService
from tests.conftest import start_campaign
from tests.test_game_core import _seed


def test_headless_simulation_keeps_invariants(db):
    _, campaign, _, character = _seed(db)
    report = simulate_session(db, campaign.id, character.id)
    assert report.ok, report.errors
    assert report.applied
    assert report.rejected  # illegal spend / rewind expected


def test_long_playthrough_with_mock_dm(db):
    _user, campaign, character = start_campaign(db, username="play_owner")
    service = GameplayService(db)
    report = play_session(service, campaign.id, character.id)
    assert report.ok, report.errors
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert not any(i.name == "Legendary Sword" for i in state.inventory)
    service.engine.assert_invariants(character.id)