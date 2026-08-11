from app.schemas.common import CampaignCreate
from app.services.campaign import CampaignService


def test_campaign_create_sets_tone_and_opening(db):
    campaign = CampaignService(db).create(
        CampaignCreate(name="Dune of Sahara", description="Scorching sands and lost caravans.")
    )
    ws = campaign.world_state or {}
    assert ws.get("tone")
    assert ws.get("opening_narration")
    assert ws.get("themes")
    assert ws.get("opening_delivered") is False
