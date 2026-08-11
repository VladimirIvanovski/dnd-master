import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Memory


class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.strip().lower().encode()).hexdigest()

    def exists_hash(self, campaign_id: uuid.UUID, content_hash: str) -> bool:
        return (
            self.db.scalar(
                select(Memory.id).where(
                    Memory.campaign_id == campaign_id,
                    Memory.content_hash == content_hash,
                )
            )
            is not None
        )

    def create(
        self,
        campaign_id: uuid.UUID,
        content: str,
        embedding: list[float] | None,
        *,
        importance: int = 5,
        entity_ids: list[str] | None = None,
        location_id: uuid.UUID | None = None,
        quest_ids: list[str] | None = None,
        event_id: uuid.UUID | None = None,
    ) -> Memory | None:
        ch = self.content_hash(content)
        if self.exists_hash(campaign_id, ch):
            return None
        memory = Memory(
            campaign_id=campaign_id,
            content=content,
            content_hash=ch,
            embedding=embedding,
            importance=importance,
            entity_ids=entity_ids or [],
            location_id=location_id,
            quest_ids=quest_ids or [],
            event_id=event_id,
        )
        self.db.add(memory)
        self.db.flush()
        return memory

    def recent(self, campaign_id: uuid.UUID, limit: int = 10) -> list[Memory]:
        return list(
            self.db.scalars(
                select(Memory)
                .where(Memory.campaign_id == campaign_id)
                .order_by(Memory.created_at.desc())
                .limit(limit)
            ).all()
        )

    def semantic_search(
        self,
        campaign_id: uuid.UUID,
        query_embedding: list[float],
        *,
        limit: int = 8,
    ) -> list[tuple[Memory, float]]:
        distance = Memory.embedding.cosine_distance(query_embedding)
        rows = self.db.execute(
            select(Memory, distance.label("distance"))
            .where(Memory.campaign_id == campaign_id, Memory.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        ).all()
        return [(row[0], float(row[1])) for row in rows]
