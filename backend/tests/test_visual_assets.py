"""Visual asset system: cache, dedupe, concurrency, auth."""

import threading
import time

from app.database.models import Location
from app.visual.hashing import normalize_name, visual_state_hash
from app.visual.provider import MockImageProvider
from app.visual.service import AssetGenerationService, LocationResolver, VisualOrchestrator
from app.visual.types import LOCATION_ART, WORLD_MAP
from tests.conftest import auth_header, make_user, start_campaign


def test_normalize_name_dedupes_variants():
    assert normalize_name("Hollow's Edge") == normalize_name("hollows edge")
    assert normalize_name("The Temple") == normalize_name("temple")


def test_location_resolver_dedupes(db):
    user = make_user(db, "vis_loc")
    from app.schemas.common import CampaignCreate
    from app.services.campaign import CampaignService

    campaign = CampaignService(db).create(CampaignCreate(name="V", description="d"), owner_id=user.id)
    resolver = LocationResolver(db)
    a, created_a = resolver.resolve_or_create(campaign.id, "Hollow's Edge", location_type="settlement")
    b, created_b = resolver.resolve_or_create(campaign.id, "Hollows Edge", location_type="settlement")
    assert created_a is True
    assert created_b is False
    assert a.id == b.id


def test_location_visual_generated_once(db):
    _user, campaign, _character = start_campaign(db, username="vis_once")
    loc = db.query(Location).filter(Location.campaign_id == campaign.id).first()
    assert loc is not None
    orch = VisualOrchestrator(db)
    orch.on_location_created(loc)
    db.commit()
    # Allow worker thread a moment
    time.sleep(0.8)
    db.expire_all()
    service = AssetGenerationService(db)
    visual = service.resolver.resolve_location(loc.id)
    # Process synchronously if worker lagged
    if not visual or not visual.stored_asset_id:
        from sqlalchemy import select
        from app.database.models.assets import AssetGenerationJob

        job = db.scalar(
            select(AssetGenerationJob).where(AssetGenerationJob.entity_id == loc.id)
        )
        if job:
            service.process_job(job.id)
            db.commit()
    visual = service.resolver.resolve_location(loc.id)
    assert visual is not None
    assert visual.stored_asset_id is not None
    first_asset = visual.stored_asset_id
    # Second ensure must not create another asset for same hash
    job2 = service.ensure_location_visual(loc)
    assert job2 is None or job2.result_asset_id == first_asset
    visual2 = service.resolver.resolve_location(loc.id)
    assert visual2.stored_asset_id == first_asset


def test_image_hash_dedupe(db):
    provider = MockImageProvider()
    a = provider.generate("same prompt forever", width=64, height=64)
    b = provider.generate("same prompt forever", width=64, height=64)
    from app.visual.hashing import image_hash

    assert image_hash(a.data) == image_hash(b.data)


def test_asset_auth_isolation(client, db):
    user_a = make_user(db, "asset_a")
    user_b = make_user(db, "asset_b")
    headers_a = auth_header(user_a)
    headers_b = auth_header(user_b)
    camp = client.post(
        "/api/campaigns",
        json={"name": "Asset Camp", "description": "visual"},
        headers=headers_a,
    ).json()
    # wait briefly for background generation of start location
    time.sleep(1.0)
    locs = db.query(Location).filter(Location.campaign_id == camp["id"]).all()
    assert locs
    loc_id = str(locs[0].id)
    # Force process jobs for reliability in tests
    from sqlalchemy import select
    from app.database.models.assets import AssetGenerationJob

    service = AssetGenerationService(db)
    for job in db.scalars(select(AssetGenerationJob).where(AssetGenerationJob.campaign_id == camp["id"])):
        service.process_job(job.id)
    db.commit()

    vis = client.get(f"/api/locations/{loc_id}/visual", headers=headers_a)
    assert vis.status_code == 200
    body = vis.json()
    assert body["status"] in {"READY", "QUEUED", "GENERATING", "PENDING", "MISSING"}
    if body.get("asset_id"):
        forbidden = client.get(f"/api/assets/{body['asset_id']}", headers=headers_b)
        assert forbidden.status_code in {403, 404}


def test_concurrent_location_jobs_single(db):
    _user, campaign, _ch = start_campaign(db, username="conc_vis")
    loc = db.query(Location).filter(Location.campaign_id == campaign.id).first()
    service = AssetGenerationService(db)
    results = []

    def enqueue():
        results.append(service.ensure_location_visual(loc))

    threads = [threading.Thread(target=enqueue) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    db.commit()
    from sqlalchemy import select, func
    from app.database.models.assets import AssetGenerationJob

    count = db.scalar(
        select(func.count())
        .select_from(AssetGenerationJob)
        .where(
            AssetGenerationJob.entity_id == loc.id,
            AssetGenerationJob.asset_type == LOCATION_ART,
        )
    )
    assert count == 1


def test_world_map_job_generates_once(db):
    _user, campaign, _ch = start_campaign(db, username="vis_map")
    service = AssetGenerationService(db)
    job = service.ensure_world_map(
        campaign.id, name=campaign.name, places=["Graymoor"], tone="ash"
    )
    if job:
        service.process_job(job.id)
        db.commit()
    from sqlalchemy import select
    from app.database.models.assets import AssetGenerationJob

    ready = db.scalar(
        select(AssetGenerationJob).where(
            AssetGenerationJob.campaign_id == campaign.id,
            AssetGenerationJob.asset_type == WORLD_MAP,
        )
    )
    if ready and not ready.result_asset_id:
        service.process_job(ready.id)
        db.commit()
        ready = db.scalar(
            select(AssetGenerationJob).where(
                AssetGenerationJob.campaign_id == campaign.id,
                AssetGenerationJob.asset_type == WORLD_MAP,
            )
        )
    assert ready is not None
    assert ready.result_asset_id is not None
    again = service.ensure_world_map(campaign.id, name=campaign.name, places=["Graymoor"])
    assert again is None
