from uuid import UUID

from app.database.repositories.world import NPCRepository
from app.schemas.common import CampaignCreate
from app.services.campaign import CampaignService
from app.utils.npc_variety import random_starter_npcs


def test_random_starter_npcs_are_varied():
    batch_a = {(n.name, n.title) for n in random_starter_npcs(2)}
    batch_b = {(n.name, n.title) for n in random_starter_npcs(2)}
    assert len(batch_a) == 2
    assert len(batch_b) == 2


def test_campaign_spawns_varied_starter_npcs(db):
    a = CampaignService(db).create(CampaignCreate(name="World A", description="Desert intrigue"))
    b = CampaignService(db).create(CampaignCreate(name="World B", description="Frozen coasts"))
    npcs_a = NPCRepository(db).nearby(UUID(a.world_state["starting_location_id"]))
    npcs_b = NPCRepository(db).nearby(UUID(b.world_state["starting_location_id"]))
    assert len(npcs_a) >= 1
    assert len(npcs_b) >= 1
    assert all(n.name != "Old Marta" for n in (*npcs_a, *npcs_b))
    assert {n.name for n in npcs_a}
    assert {n.name for n in npcs_b}
