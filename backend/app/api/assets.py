from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.security import get_current_user, require_campaign_access, require_character_access
from app.core.rate_limit import limiter
from app.database.models import Campaign, Character, Item, Location, NPC, User
from app.database.models.assets import (
    AssetGenerationJob,
    CharacterAppearance,
    ItemVisual,
    LocationVisual,
    NpcAppearance,
    StoredAsset,
)
from app.database.repositories import CampaignRepository
from app.visual import AssetGenerationService, AssetResolver, AssetService, spawn_asset_worker
from app.visual.hashing import visual_state_hash
from app.visual.storage import AssetStorageService
from app.visual.types import CHARACTER_PORTRAIT, ITEM_ICON, JOB_QUEUED, LOCATION_ART, NPC_PORTRAIT, WORLD_MAP


def _kick_queued_jobs(db: Session, entity_id: uuid.UUID, asset_types: list[str]) -> None:
    """Re-spawn workers for stuck QUEUED jobs (e.g. after pre-commit spawn races)."""
    jobs = db.scalars(
        select(AssetGenerationJob).where(
            AssetGenerationJob.entity_id == entity_id,
            AssetGenerationJob.asset_type.in_(asset_types),
            AssetGenerationJob.state == JOB_QUEUED,
        )
    ).all()
    for job in jobs:
        spawn_asset_worker(job.id)

router = APIRouter(tags=["assets"])


class AssetOut(BaseModel):
    id: uuid.UUID
    asset_type: str
    url: str
    width: int
    height: int
    mime_type: str
    status: str = "READY"


class JobOut(BaseModel):
    id: uuid.UUID
    state: str
    asset_type: str
    entity_id: uuid.UUID
    error: str = ""


def _campaign_owns_asset(db: Session, user: User, asset: StoredAsset) -> bool:
    if asset.is_library:
        return True
    if asset.campaign_id is None:
        return False
    try:
        require_campaign_access(db, asset.campaign_id, user)
        return True
    except HTTPException:
        return False


@router.get("/api/assets/{asset_id}")
def get_asset_file(
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    asset = db.get(StoredAsset, asset_id)
    if not asset or not _campaign_owns_asset(db, user, asset):
        raise HTTPException(status_code=404, detail="Asset not found")
    storage = AssetStorageService()
    path = storage.absolute_path(asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Asset file missing")
    return FileResponse(path, media_type=asset.mime_type)


@router.get("/api/assets/{asset_id}/meta", response_model=AssetOut)
def get_asset_meta(
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    asset = db.get(StoredAsset, asset_id)
    if not asset or not _campaign_owns_asset(db, user, asset):
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetOut(
        id=asset.id,
        asset_type=asset.asset_type,
        url=f"/api/assets/{asset.id}",
        width=asset.width,
        height=asset.height,
        mime_type=asset.mime_type,
    )


@router.get("/api/locations/{location_id}/visual")
def location_visual(
    location_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    require_campaign_access(db, loc.campaign_id, user)
    # Re-ensure so richer detail prompts / higher res can queue when hash changes.
    job = AssetGenerationService(db).ensure_location_visual(loc)
    db.commit()
    if job and job.state == JOB_QUEUED:
        spawn_asset_worker(job.id)

    visual = AssetResolver(db).resolve_location(location_id)
    if visual and visual.stored_asset_id and visual.visual_state_hash == loc.visual_state_hash:
        asset = db.get(StoredAsset, visual.stored_asset_id)
        if asset:
            return {
                "status": "READY",
                "asset_id": str(asset.id),
                "url": f"/api/assets/{asset.id}",
                "version": visual.version,
            }
    # While regenerating, still show previous art if present.
    if visual and visual.stored_asset_id and (job is None or job.state != "READY"):
        asset = db.get(StoredAsset, visual.stored_asset_id)
        if asset and job and job.state in {JOB_QUEUED, "GENERATING"}:
            return {
                "status": job.state,
                "asset_id": str(asset.id),
                "url": f"/api/assets/{asset.id}",
                "version": visual.version,
                "upgrading": True,
            }
        if asset and job is None:
            return {
                "status": "READY",
                "asset_id": str(asset.id),
                "url": f"/api/assets/{asset.id}",
                "version": visual.version,
            }
    _kick_queued_jobs(db, location_id, [LOCATION_ART, "ROOM_ART"])
    pending = db.scalar(
        select(AssetGenerationJob)
        .where(
            AssetGenerationJob.entity_id == location_id,
            AssetGenerationJob.asset_type.in_([LOCATION_ART, "ROOM_ART"]),
        )
        .order_by(AssetGenerationJob.created_at.desc())
    )
    if pending and pending.state != "READY":
        return {"status": pending.state, "job_id": str(pending.id), "url": None}
    return {"status": "MISSING", "url": None}


@router.get("/api/npcs/{npc_id}/portrait")
def npc_portrait(
    npc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    npc = db.get(NPC, npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    require_campaign_access(db, npc.campaign_id, user)
    app = AssetResolver(db).resolve_npc(npc_id)
    if app and app.stored_asset_id:
        return {"status": "READY", "asset_id": str(app.stored_asset_id), "url": f"/api/assets/{app.stored_asset_id}"}
    _kick_queued_jobs(db, npc_id, [NPC_PORTRAIT])
    return {"status": "PENDING", "url": None}


@router.get("/api/characters/{character_id}/portrait")
def character_portrait(
    character_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    require_character_access(db, character_id, user)
    app = AssetResolver(db).resolve_character(character_id)
    if app and app.stored_asset_id:
        return {
            "status": "READY",
            "asset_id": str(app.stored_asset_id),
            "url": f"/api/assets/{app.stored_asset_id}",
        }
    _kick_queued_jobs(db, character_id, [CHARACTER_PORTRAIT])
    return {"status": "PENDING", "url": None}


@router.get("/api/items/{item_id}/icon")
def item_icon(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    require_campaign_access(db, item.campaign_id, user)
    vis = AssetResolver(db).resolve_item(item_id)
    if vis and vis.stored_asset_id:
        return {"status": "READY", "asset_id": str(vis.stored_asset_id), "url": f"/api/assets/{vis.stored_asset_id}"}
    _kick_queued_jobs(db, item_id, [ITEM_ICON])
    return {"status": "PENDING", "url": None}


@router.get("/api/campaigns/{campaign_id}/map")
def campaign_map(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    require_campaign_access(db, campaign_id, user)
    campaign = db.get(Campaign, campaign_id)
    locs = list(
        db.scalars(select(Location).where(Location.campaign_id == campaign_id, Location.discovered.is_(True))).all()
    )
    if not locs:
        locs = list(db.scalars(select(Location).where(Location.campaign_id == campaign_id)).all())
    nodes = []
    for i, loc in enumerate(locs):
        coords = loc.coordinates or {}
        raw_x = coords.get("x")
        raw_y = coords.get("y")
        if isinstance(raw_x, (int, float)) and isinstance(raw_y, (int, float)) and (raw_x > 20 or raw_y > 20):
            x, y = float(raw_x), float(raw_y)
        else:
            x = 80 + (i % 5) * 100
            y = 80 + (i // 5) * 80
        nodes.append(
            {
                "id": str(loc.id),
                "name": loc.name,
                "type": loc.location_type,
                "parent_id": str(loc.parent_id) if loc.parent_id else None,
                "x": x,
                "y": y,
                "active_visual_id": str(loc.active_visual_id) if loc.active_visual_id else None,
            }
        )

    # Ensure / kick world map art (generate once per campaign).
    art_status = "MISSING"
    art_url = None
    art_asset_id = None
    if campaign:
        service = AssetGenerationService(db)
        job = service.ensure_world_map(
            campaign_id,
            name=campaign.name,
            description=campaign.description or "",
            places=[n["name"] for n in nodes],
            tone=str((campaign.world_state or {}).get("tone") or ""),
        )
        db.commit()
        if job and job.state == JOB_QUEUED:
            spawn_asset_worker(job.id)
        ready = db.scalar(
            select(AssetGenerationJob).where(
                AssetGenerationJob.campaign_id == campaign_id,
                AssetGenerationJob.entity_id == campaign_id,
                AssetGenerationJob.asset_type == WORLD_MAP,
                AssetGenerationJob.state == "READY",
                AssetGenerationJob.result_asset_id.is_not(None),
            )
        )
        if ready and ready.result_asset_id:
            art_status = "READY"
            art_asset_id = str(ready.result_asset_id)
            art_url = f"/api/assets/{ready.result_asset_id}"
        elif job:
            art_status = job.state
        else:
            _kick_queued_jobs(db, campaign_id, [WORLD_MAP])
            pending = db.scalar(
                select(AssetGenerationJob)
                .where(
                    AssetGenerationJob.entity_id == campaign_id,
                    AssetGenerationJob.asset_type == WORLD_MAP,
                )
                .order_by(AssetGenerationJob.created_at.desc())
            )
            if pending:
                art_status = pending.state

    return {
        "campaign_id": str(campaign_id),
        "locations": nodes,
        "art_status": art_status,
        "art_url": art_url,
        "art_asset_id": art_asset_id,
    }


@router.post("/api/assets/{asset_id}/regenerate")
@limiter.limit("5/minute")
def regenerate_asset(
    request: Request,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    asset = db.get(StoredAsset, asset_id)
    if not asset or not _campaign_owns_asset(db, user, asset):
        raise HTTPException(status_code=404, detail="Asset not found")
    # Controlled regen: re-queue by entity from character portrait only for now
    raise HTTPException(status_code=400, detail="Use entity-specific regenerate endpoints")


@router.post("/api/characters/{character_id}/portrait/regenerate")
@limiter.limit("5/minute")
def regenerate_character_portrait(
    request: Request,
    character_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    _, character = require_character_access(db, character_id, user)
    for app in db.scalars(
        select(CharacterAppearance).where(
            CharacterAppearance.character_id == character_id,
            CharacterAppearance.is_active.is_(True),
        )
    ):
        app.is_active = False
        app.stored_asset_id = None
    service = AssetGenerationService(db)
    job = service.ensure_character_portrait(character)
    db.commit()
    if job:
        spawn_asset_worker(job.id)
        return {"status": job.state, "job_id": str(job.id)}
    return {"status": "READY"}


@router.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    job = db.get(AssetGenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    require_campaign_access(db, job.campaign_id, user)
    return JobOut(
        id=job.id,
        state=job.state,
        asset_type=job.asset_type,
        entity_id=job.entity_id,
        error=job.error or "",
    )
