import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Event


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        campaign_id: uuid.UUID,
        event_type: str,
        summary: str,
        *,
        character_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        payload: dict | None = None,
        importance: int = 5,
    ) -> Event:
        event = Event(
            campaign_id=campaign_id,
            character_id=character_id,
            event_type=event_type,
            summary=summary,
            location_id=location_id,
            payload=payload or {},
            importance=importance,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def recent(
        self,
        campaign_id: uuid.UUID,
        *,
        limit: int = 20,
        character_id: uuid.UUID | None = None,
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(Event.campaign_id == campaign_id)
            .order_by(Event.created_at.desc())
            .limit(limit)
        )
        if character_id:
            stmt = stmt.where(
                (Event.character_id == character_id) | (Event.character_id.is_(None))
            )
        return list(self.db.scalars(stmt).all())
