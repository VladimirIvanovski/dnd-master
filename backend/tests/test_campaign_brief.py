from app.schemas.common import CampaignCreate
from app.services.campaign import CampaignService
from tests.conftest import make_user


def test_campaign_create_sets_tone_and_opening(db):
    user = make_user(db, username="brief_user")
    campaign = CampaignService(db).create(
        CampaignCreate(name="Dune of Sahara", description="Scorching sands and lost caravans."),
        owner_id=user.id,
    )
    ws = campaign.world_state or {}
    assert ws.get("tone")
    assert ws.get("opening_narration")
    assert ws.get("themes")
    assert ws.get("opening_delivered") is False
    assert "campaign_dna" in ws
    assert ws["campaign_dna"].get("version") == 1
    assert ws.get("user_campaign_description") == "Scorching sands and lost caravans."
    rumors = ws.get("rumors") or []
    assert len(rumors) >= 2
    assert all(not r.get("heard") for r in rumors)
