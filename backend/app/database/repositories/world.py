import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Location, NPC, Quest, Relationship


class LocationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, campaign_id: uuid.UUID, name: str, **kwargs) -> Location:
        loc = Location(campaign_id=campaign_id, name=name, **kwargs)
        self.db.add(loc)
        self.db.flush()
        return loc

    def get(self, location_id: uuid.UUID) -> Location | None:
        return self.db.get(Location, location_id)


class NPCRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, campaign_id: uuid.UUID, name: str, **kwargs) -> NPC:
        npc = NPC(campaign_id=campaign_id, name=name, **kwargs)
        self.db.add(npc)
        self.db.flush()
        return npc

    def find_at_location(
        self, campaign_id: uuid.UUID, location_id: uuid.UUID, name: str
    ) -> NPC | None:
        return self.db.scalar(
            select(NPC).where(
                NPC.campaign_id == campaign_id,
                NPC.location_id == location_id,
                NPC.name.ilike(name.strip()),
            )
        )

    def nearby(self, location_id: uuid.UUID, *, alive_only: bool = True) -> list[NPC]:
        stmt = select(NPC).where(NPC.location_id == location_id)
        if alive_only:
            stmt = stmt.where(NPC.is_alive.is_(True))
        return list(self.db.scalars(stmt).all())

    def get(self, npc_id: uuid.UUID) -> NPC | None:
        return self.db.get(NPC, npc_id)


class QuestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, campaign_id: uuid.UUID, title: str, **kwargs) -> Quest:
        quest = Quest(campaign_id=campaign_id, title=title, **kwargs)
        self.db.add(quest)
        self.db.flush()
        return quest

    def get(self, quest_id: uuid.UUID) -> Quest | None:
        return self.db.scalar(
            select(Quest)
            .options(joinedload(Quest.objectives))
            .where(Quest.id == quest_id)
        )

    def active_for_campaign(
        self, campaign_id: uuid.UUID, character_id: uuid.UUID | None = None
    ) -> list[Quest]:
        stmt = (
            select(Quest)
            .options(joinedload(Quest.objectives))
            .where(Quest.campaign_id == campaign_id, Quest.status == "active")
        )
        if character_id:
            stmt = stmt.where(
                (Quest.character_id == character_id) | (Quest.character_id.is_(None))
            )
        return list(self.db.scalars(stmt).unique().all())


class RelationshipRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, character_id: uuid.UUID, npc_id: uuid.UUID) -> Relationship:
        rel = self.db.scalar(
            select(Relationship).where(
                Relationship.character_id == character_id,
                Relationship.npc_id == npc_id,
            )
        )
        if rel:
            return rel
        rel = Relationship(character_id=character_id, npc_id=npc_id)
        self.db.add(rel)
        self.db.flush()
        return rel
