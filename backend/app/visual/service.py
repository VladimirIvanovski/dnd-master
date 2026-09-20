from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models.assets import (
    AssetGenerationJob,
    CharacterAppearance,
    ItemVisual,
    LocationVisual,
    NpcAppearance,
    StoredAsset,
)
from app.database.models.character import Character
from app.database.models.item import Item
from app.database.models.location import Location
from app.database.models.npc import NPC
from app.database.session import SessionLocal
from app.utils.ids import utcnow
from app.visual.hashing import image_hash, normalize_name, visual_state_hash
from app.visual.prompts import SceneVisualPromptBuilder
from app.visual.provider import get_image_provider
from app.visual.storage import AssetStorageService
from app.visual.types import (
    CHARACTER_PORTRAIT,
    GENERIC_ITEMS,
    ITEM_ICON,
    JOB_FAILED,
    JOB_GENERATING,
    JOB_QUEUED,
    JOB_READY,
    LOCATION_ART,
    NPC_PORTRAIT,
    PROFILES,
    ROOM_ART,
    WORLD_MAP,
)

logger = logging.getLogger(__name__)
_worker_lock = threading.Lock()
_active_workers = 0


class LocationResolver:
    def __init__(self, db: Session):
        self.db = db

    def find_existing(
        self,
        campaign_id: uuid.UUID,
        name: str,
        *,
        parent_id: uuid.UUID | None = None,
        location_type: str | None = None,
    ) -> Location | None:
        norm = normalize_name(name)
        stmt = select(Location).where(
            Location.campaign_id == campaign_id,
            Location.normalized_name == norm,
        )
        if parent_id is not None:
            stmt = stmt.where(Location.parent_id == parent_id)
        else:
            stmt = stmt.where(Location.parent_id.is_(None))
        if location_type:
            stmt = stmt.where(Location.location_type == location_type)
        return self.db.scalar(stmt)

    def resolve_or_create(
        self,
        campaign_id: uuid.UUID,
        name: str,
        *,
        parent_id: uuid.UUID | None = None,
        location_type: str = "settlement",
        description: str = "",
        **kwargs: Any,
    ) -> tuple[Location, bool]:
        existing = self.find_existing(
            campaign_id, name, parent_id=parent_id, location_type=location_type
        )
        if existing:
            return existing, False
        loc = Location(
            campaign_id=campaign_id,
            name=name[:128],
            normalized_name=normalize_name(name),
            parent_id=parent_id,
            location_type=location_type,
            description=description,
            **kwargs,
        )
        self.db.add(loc)
        self.db.flush()
        return loc, True


class AssetService:
    def __init__(self, db: Session, storage: AssetStorageService | None = None):
        self.db = db
        self.storage = storage or AssetStorageService()

    def get_asset(self, asset_id: uuid.UUID) -> StoredAsset | None:
        return self.db.get(StoredAsset, asset_id)

    def find_by_hash(self, digest: str) -> StoredAsset | None:
        return self.db.scalar(select(StoredAsset).where(StoredAsset.image_hash == digest))

    def find_library(self, library_key: str) -> StoredAsset | None:
        return self.db.scalar(select(StoredAsset).where(StoredAsset.library_key == library_key))

    def public_url(self, asset_id: uuid.UUID) -> str:
        return f"/api/assets/{asset_id}"


class AssetResolver:
    def __init__(self, db: Session):
        self.db = db
        self.assets = AssetService(db)

    def resolve_location(self, location_id: uuid.UUID) -> LocationVisual | None:
        return self.db.scalar(
            select(LocationVisual).where(
                LocationVisual.location_id == location_id,
                LocationVisual.is_active.is_(True),
            )
        )

    def resolve_npc(self, npc_id: uuid.UUID) -> NpcAppearance | None:
        return self.db.scalar(
            select(NpcAppearance).where(
                NpcAppearance.npc_id == npc_id,
                NpcAppearance.is_active.is_(True),
            )
        )

    def resolve_character(self, character_id: uuid.UUID) -> CharacterAppearance | None:
        return self.db.scalar(
            select(CharacterAppearance).where(
                CharacterAppearance.character_id == character_id,
                CharacterAppearance.is_active.is_(True),
            )
        )

    def resolve_item(self, item_id: uuid.UUID) -> ItemVisual | None:
        return self.db.scalar(select(ItemVisual).where(ItemVisual.item_id == item_id))


class AssetGenerationService:
    """Queue + process visual jobs without blocking gameplay."""

    MAX_ATTEMPTS = 3

    def __init__(self, db: Session):
        self.db = db
        self.resolver = AssetResolver(db)
        self.assets = AssetService(db)
        self.storage = AssetStorageService()
        self.settings = get_settings()

    def ensure_location_visual(self, location: Location) -> AssetGenerationJob | None:
        self._enrich_location_visual_fields(location)
        nearby = self._nearby_elements_line(location)
        state = {
            "location_id": str(location.id),
            "biome": location.biome or "",
            "architecture": location.architecture or "",
            "terrain": location.terrain or "",
            "atmosphere": location.atmosphere or "",
            "weather": location.weather or "clear",
            "time_of_day": location.time_of_day or "day",
            "important_features": location.important_features or [],
            "nearby_elements": nearby,
            "damage_state": (location.extra or {}).get("damage_state", "intact"),
            "location_type": location.location_type,
            "name": location.name,
            "description": (location.description or "")[:200],
            "detail": "v3-surroundings",
        }
        vhash = visual_state_hash(state)
        location.visual_state_hash = vhash
        existing = self.db.scalar(
            select(LocationVisual).where(
                LocationVisual.location_id == location.id,
                LocationVisual.visual_state_hash == vhash,
                LocationVisual.stored_asset_id.is_not(None),
            )
        )
        if existing:
            location.active_visual_id = existing.id
            return None
        asset_type = ROOM_ART if location.location_type in {"room", "area", "chamber"} else LOCATION_ART
        prompt = SceneVisualPromptBuilder.location(
            {
                "name": location.name,
                "location_type": location.location_type,
                "biome": location.biome,
                "terrain": location.terrain,
                "architecture": location.architecture,
                "atmosphere": location.atmosphere,
                "weather": location.weather or "clear",
                "time_of_day": location.time_of_day or "day",
                "important_features": location.important_features or [],
                "nearby_elements": nearby,
                "description": location.description or "",
                "visual_style": location.visual_style or "dark fantasy oil painting",
            }
        )
        location.visual_prompt = prompt
        return self._enqueue(location.campaign_id, location.id, asset_type, prompt, vhash)

    @staticmethod
    def _nearby_elements_line(location: Location) -> str:
        feats = location.important_features or []
        bits = [str(f) for f in feats[:4]]
        if location.architecture:
            bits.append(str(location.architecture).split(",")[0].strip())
        if location.terrain:
            bits.append(str(location.terrain).split(",")[0].strip())
        return ", ".join(bits[:5])

    @staticmethod
    def _enrich_location_visual_fields(location: Location) -> None:
        """Fill empty visual metadata so prompts show concrete surroundings."""
        text = f"{location.name} {location.description} {location.location_type}".lower()
        if not location.biome:
            if any(w in text for w in ("desert", "dune", "arid", "sand")):
                location.biome = "sun-bleached desert marches"
            elif any(w in text for w in ("forest", "wood", "grove", "tree")):
                location.biome = "ancient shadowed forest"
            elif any(w in text for w in ("coast", "sea", "harbor", "port", "shore")):
                location.biome = "windswept coastal lands"
            elif any(w in text for w in ("mountain", "peak", "pass", "ridge")):
                location.biome = "rugged mountain frontier"
            elif any(w in text for w in ("swamp", "marsh", "bog")):
                location.biome = "misty marshlands"
            elif any(w in text for w in ("snow", "ice", "winter", "frost")):
                location.biome = "frozen northern wilds"
            elif any(w in text for w in ("outpost", "settlement", "town", "village", "city")):
                location.biome = "frontier settlement lands"
            else:
                location.biome = "frontier fantasy countryside"
        if not location.terrain:
            if any(w in text for w in ("street", "road", "cobble", "plaza")):
                location.terrain = "cobbled street, packed earth edges, gutters"
            elif any(w in text for w in ("dune", "sand")):
                location.terrain = "drifting sand, rocky shelves, wind-cut ridges"
            elif any(w in text for w in ("cave", "tunnel", "mine")):
                location.terrain = "uneven stone floor, rubble, damp rock walls"
            else:
                location.terrain = "worn path underfoot, uneven ground, distant horizon"
        if not location.architecture:
            if location.location_type in {"dungeon", "ruin", "temple", "tomb"}:
                location.architecture = "crumbling stone halls, arches, torch niches, debris"
            elif location.location_type in {"room", "area", "chamber", "inn", "tavern"}:
                location.architecture = "timber beams, hearth glow, worn tables, shuttered windows"
            elif any(w in text for w in ("outpost", "fort", "wall", "gate")):
                location.architecture = "palisade walls, watch posts, rough timber gates"
            else:
                location.architecture = "timber-framed buildings, stone foundations, thatch or slate roofs"
        if not location.atmosphere:
            location.atmosphere = "grounded, readable, cinematic depth"
        if not location.weather:
            location.weather = "clear"
        if not location.time_of_day:
            location.time_of_day = "day"
        if not location.important_features:
            features: list[str] = []
            if any(w in text for w in ("tavern", "inn", "hearth")):
                features = ["wooden door", "hanging sign", "warm window light", "street outside"]
            elif any(w in text for w in ("market", "stall", "bazaar")):
                features = ["market stalls", "crates and barrels", "awning cloth", "busy lane"]
            elif any(w in text for w in ("gate", "wall", "outpost")):
                features = ["main gate", "watch platform", "approach road", "banner poles"]
            elif any(w in text for w in ("dune", "desert", "sand")):
                features = ["sand ridge", "wind-blown ash", "distant rock spires", "travel track"]
            elif location.location_type in {"dungeon", "ruin", "cave"}:
                features = ["broken archway", "scattered rubble", "torch niches", "shadowed passage"]
            else:
                features = [
                    "clear foreground path",
                    "nearby landmark structures",
                    "usable props (cart, crates, well)",
                    "distant landscape backdrop",
                ]
            location.important_features = features
        if not location.visual_style or location.visual_style == "dark fantasy RPG":
            location.visual_style = "dark fantasy oil painting"
    def ensure_world_map(self, campaign_id: uuid.UUID, *, name: str, description: str = "", places: list[str] | None = None, tone: str = "") -> AssetGenerationJob | None:
        ready = self.db.scalar(
            select(AssetGenerationJob).where(
                AssetGenerationJob.campaign_id == campaign_id,
                AssetGenerationJob.entity_id == campaign_id,
                AssetGenerationJob.asset_type == WORLD_MAP,
                AssetGenerationJob.state == JOB_READY,
                AssetGenerationJob.result_asset_id.is_not(None),
            )
        )
        if ready:
            return None
        queued = self.db.scalar(
            select(AssetGenerationJob).where(
                AssetGenerationJob.campaign_id == campaign_id,
                AssetGenerationJob.entity_id == campaign_id,
                AssetGenerationJob.asset_type == WORLD_MAP,
                AssetGenerationJob.state.in_([JOB_QUEUED, JOB_GENERATING]),
            )
        )
        if queued:
            return queued
        place_list = places or []
        vhash = visual_state_hash({"campaign_id": str(campaign_id), "kind": "world_map"})
        prompt = SceneVisualPromptBuilder.world_map(
            {
                "name": name,
                "tone": tone or description[:120],
                "places": place_list[:8],
            }
        )
        return self._enqueue(campaign_id, campaign_id, WORLD_MAP, prompt, vhash)

    def ensure_npc_portrait(self, npc: NPC) -> AssetGenerationJob | None:
        active = self.resolver.resolve_npc(npc.id)
        if active and active.stored_asset_id:
            return None
        appearance = (npc.extra or {}).get("appearance") or self._default_npc_appearance(npc)
        vhash = visual_state_hash(appearance)
        if not active:
            active = NpcAppearance(
                npc_id=npc.id,
                appearance=appearance,
                visual_state_hash=vhash,
                version=1,
                is_active=True,
            )
            self.db.add(active)
            self.db.flush()
        elif active.visual_state_hash == vhash and active.stored_asset_id:
            return None
        prompt = SceneVisualPromptBuilder.npc(appearance, name=npc.name, title=npc.title)
        return self._enqueue(npc.campaign_id, npc.id, NPC_PORTRAIT, prompt, vhash)

    def ensure_character_portrait(self, character: Character) -> AssetGenerationJob | None:
        active = self.resolver.resolve_character(character.id)
        if active and active.stored_asset_id:
            return None
        appearance = (character.extra or {}).get("appearance") or self._default_character_appearance(
            character
        )
        vhash = visual_state_hash(appearance)
        if not active:
            active = CharacterAppearance(
                character_id=character.id,
                appearance=appearance,
                visual_state_hash=vhash,
                version=1,
                is_active=True,
            )
            self.db.add(active)
            self.db.flush()
        prompt = SceneVisualPromptBuilder.character(
            appearance, name=character.name, class_name=character.class_name
        )
        return self._enqueue(
            character.campaign_id, character.id, CHARACTER_PORTRAIT, prompt, vhash
        )

    def ensure_item_icon(self, item: Item) -> AssetGenerationJob | None:
        existing = self.resolver.resolve_item(item.id)
        if existing and existing.stored_asset_id:
            return None
        norm = normalize_name(item.name)
        for key, library_key in GENERIC_ITEMS.items():
            if key in norm or norm == key:
                lib = self.assets.find_library(library_key)
                if lib:
                    vis = ItemVisual(
                        item_id=item.id,
                        campaign_id=item.campaign_id,
                        library_key=library_key,
                        visual_meta={"type": item.item_type, "name": item.name},
                        visual_state_hash=visual_state_hash({"library_key": library_key}),
                        stored_asset_id=lib.id,
                    )
                    self.db.add(vis)
                    self.db.flush()
                    return None
                # Queue library asset once, then bind
                meta = {"type": item.item_type or "misc", "shape": item.name, "name": item.name}
                vhash = visual_state_hash({"library_key": library_key})
                prompt = SceneVisualPromptBuilder.item(meta, name=item.name)
                job = self._enqueue(
                    item.campaign_id,
                    item.id,
                    ITEM_ICON,
                    prompt,
                    vhash,
                    params={"library_key": library_key},
                )
                if not existing:
                    self.db.add(
                        ItemVisual(
                            item_id=item.id,
                            campaign_id=item.campaign_id,
                            library_key=library_key,
                            visual_meta=meta,
                            visual_state_hash=vhash,
                        )
                    )
                    self.db.flush()
                return job

        meta = {
            "type": item.item_type or "misc",
            "material": (item.properties or {}).get("material", ""),
            "color": (item.properties or {}).get("color", ""),
            "shape": item.name,
            "rarity": (item.properties or {}).get("rarity", "common"),
            "visual_style": "dark fantasy",
        }
        vhash = visual_state_hash(meta)
        if not existing:
            self.db.add(
                ItemVisual(
                    item_id=item.id,
                    campaign_id=item.campaign_id,
                    visual_meta=meta,
                    visual_state_hash=vhash,
                )
            )
            self.db.flush()
        prompt = SceneVisualPromptBuilder.item(meta, name=item.name)
        return self._enqueue(item.campaign_id, item.id, ITEM_ICON, prompt, vhash)

    def _enqueue(
        self,
        campaign_id: uuid.UUID,
        entity_id: uuid.UUID,
        asset_type: str,
        prompt: str,
        vhash: str,
        params: dict | None = None,
    ) -> AssetGenerationJob | None:
        existing = self.db.scalar(
            select(AssetGenerationJob).where(
                AssetGenerationJob.campaign_id == campaign_id,
                AssetGenerationJob.entity_id == entity_id,
                AssetGenerationJob.asset_type == asset_type,
                AssetGenerationJob.visual_state_hash == vhash,
                AssetGenerationJob.state.in_([JOB_QUEUED, JOB_GENERATING, JOB_READY]),
            )
        )
        if existing:
            return existing
        job = AssetGenerationJob(
            campaign_id=campaign_id,
            entity_id=entity_id,
            asset_type=asset_type,
            prompt=prompt,
            model=self.settings.image_model,
            state=JOB_QUEUED,
            visual_state_hash=vhash,
            params=params or {},
        )
        self.db.add(job)
        try:
            with self.db.begin_nested():
                self.db.flush()
        except IntegrityError:
            return self.db.scalar(
                select(AssetGenerationJob).where(
                    AssetGenerationJob.campaign_id == campaign_id,
                    AssetGenerationJob.entity_id == entity_id,
                    AssetGenerationJob.asset_type == asset_type,
                    AssetGenerationJob.visual_state_hash == vhash,
                )
            )
        return job

    def process_job(self, job_id: uuid.UUID) -> StoredAsset | None:
        job = self.db.get(AssetGenerationJob, job_id)
        if not job or job.state == JOB_READY:
            return self.assets.get_asset(job.result_asset_id) if job and job.result_asset_id else None
        if job.state == JOB_FAILED and job.attempts >= self.MAX_ATTEMPTS:
            return None
        job.state = JOB_GENERATING
        job.attempts += 1
        self.db.flush()

        width, height, steps = PROFILES.get(job.asset_type, (512, 512, 12))
        try:
            provider = get_image_provider()
            job.model = getattr(provider, "kind", self.settings.image_model)
            generated = provider.generate(job.prompt, width=width, height=height, steps=steps)
            digest = image_hash(generated.data)
            reused = self.assets.find_by_hash(digest)
            if reused:
                asset = reused
            else:
                storage_key = f"{job.campaign_id}/{digest[:16]}.png"
                self.storage.save(storage_key, generated.data)
                library_key = (job.params or {}).get("library_key")
                asset = StoredAsset(
                    campaign_id=None if library_key else job.campaign_id,
                    asset_type=job.asset_type,
                    storage_key=storage_key,
                    image_hash=digest,
                    mime_type=generated.mime_type,
                    width=generated.width,
                    height=generated.height,
                    file_size=len(generated.data),
                    is_library=bool(library_key),
                    library_key=library_key,
                )
                self.db.add(asset)
                self.db.flush()
            self._bind_asset(job, asset)
            job.result_asset_id = asset.id
            job.state = JOB_READY
            job.completed_at = utcnow()
            job.error = ""
            self.db.flush()
            return asset
        except Exception as exc:  # noqa: BLE001
            logger.exception("Asset generation failed for job %s", job_id)
            job.state = JOB_FAILED
            job.error = str(exc)[:1000]
            self.db.flush()
            return None

    def _bind_asset(self, job: AssetGenerationJob, asset: StoredAsset) -> None:
        if job.asset_type in {LOCATION_ART, ROOM_ART}:
            loc = self.db.get(Location, job.entity_id)
            if not loc:
                return
            for old in self.db.scalars(
                select(LocationVisual).where(
                    LocationVisual.location_id == loc.id, LocationVisual.is_active.is_(True)
                )
            ):
                old.is_active = False
            version = (
                self.db.scalar(
                    select(LocationVisual.version)
                    .where(LocationVisual.location_id == loc.id)
                    .order_by(LocationVisual.version.desc())
                )
                or 0
            ) + 1
            visual = LocationVisual(
                location_id=loc.id,
                version=version,
                stored_asset_id=asset.id,
                prompt=job.prompt,
                visual_state_hash=job.visual_state_hash,
                generation_model=job.model,
                generation_parameters={"width": asset.width, "height": asset.height},
                is_active=True,
            )
            self.db.add(visual)
            self.db.flush()
            loc.active_visual_id = visual.id
            return

        if job.asset_type == NPC_PORTRAIT:
            app = self.resolver.resolve_npc(job.entity_id)
            if app:
                app.stored_asset_id = asset.id
            return
        if job.asset_type == CHARACTER_PORTRAIT:
            app = self.resolver.resolve_character(job.entity_id)
            if app:
                app.stored_asset_id = asset.id
            return
        if job.asset_type == ITEM_ICON:
            vis = self.resolver.resolve_item(job.entity_id)
            if vis:
                vis.stored_asset_id = asset.id

    @staticmethod
    def _default_npc_appearance(npc: NPC) -> dict:
        return {
            "race": "human",
            "age": "adult",
            "hair": "dark",
            "eyes": "brown",
            "skin": "tan",
            "clothing": npc.title or "traveler's garb",
            "accessories": [],
            "personality_hint": (npc.personality or "")[:80],
        }

    @staticmethod
    def _default_character_appearance(character: Character) -> dict:
        return {
            "race": character.race,
            "gender": "unspecified",
            "age": "young adult",
            "hair": "brown",
            "eyes": "brown",
            "skin": "fair",
            "face": "adventurous",
            "clothing": f"{character.class_name} attire",
            "armor": "",
            "accessories": [],
        }


def spawn_asset_worker(job_id: uuid.UUID) -> None:
    """Run generation in a background thread with concurrency limit."""
    global _active_workers
    settings = get_settings()

    def _run() -> None:
        global _active_workers
        # Wait for a worker slot instead of silently dropping the job.
        while True:
            with _worker_lock:
                if _active_workers < max(1, settings.image_max_concurrent):
                    _active_workers += 1
                    break
            time.sleep(0.15)

        db = SessionLocal()
        try:
            # Job may have been queued in another transaction; retry briefly.
            for _ in range(20):
                job = db.get(AssetGenerationJob, job_id)
                if job is not None:
                    break
                time.sleep(0.1)
                db.rollback()
            AssetGenerationService(db).process_job(job_id)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.exception("Background asset worker failed")
        finally:
            db.close()
            with _worker_lock:
                _active_workers -= 1

    threading.Thread(target=_run, daemon=True).start()


class VisualOrchestrator:
    """Facade used by campaign/gameplay services after entity creation."""

    def __init__(self, db: Session):
        self.db = db
        self.gen = AssetGenerationService(db)
        self.locations = LocationResolver(db)
        self._pending_job_ids: list[uuid.UUID] = []

    def on_location_created(self, location: Location) -> None:
        if not location.normalized_name:
            location.normalized_name = normalize_name(location.name)
        job = self.gen.ensure_location_visual(location)
        self.db.flush()
        if job and job.state == JOB_QUEUED:
            self._pending_job_ids.append(job.id)

    def on_npc_created(self, npc: NPC) -> None:
        job = self.gen.ensure_npc_portrait(npc)
        self.db.flush()
        if job and job.state == JOB_QUEUED:
            self._pending_job_ids.append(job.id)

    def on_character_created(self, character: Character) -> None:
        job = self.gen.ensure_character_portrait(character)
        self.db.flush()
        if job and job.state == JOB_QUEUED:
            self._pending_job_ids.append(job.id)

    def on_item_created(self, item: Item) -> None:
        job = self.gen.ensure_item_icon(item)
        self.db.flush()
        if job and job.state == JOB_QUEUED:
            self._pending_job_ids.append(job.id)

    def on_campaign_created(self, campaign_id: uuid.UUID, *, name: str, description: str = "", places: list[str] | None = None, tone: str = "") -> None:
        job = self.gen.ensure_world_map(
            campaign_id, name=name, description=description, places=places, tone=tone
        )
        self.db.flush()
        if job and job.state == JOB_QUEUED:
            self._pending_job_ids.append(job.id)

    def kick_workers_after_commit(self) -> None:
        """Call after db.commit() so workers can see queued jobs."""
        for job_id in self._pending_job_ids:
            spawn_asset_worker(job_id)
        self._pending_job_ids.clear()
