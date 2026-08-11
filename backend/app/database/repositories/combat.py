import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import CombatSession


class CombatRepository:
    def __init__(self, db: Session):
        self.db = db

    def active_for_campaign(self, campaign_id: uuid.UUID) -> CombatSession | None:
        return self.db.scalar(
            select(CombatSession)
            .options(joinedload(CombatSession.combatants))
            .where(
                CombatSession.campaign_id == campaign_id,
                CombatSession.status == "active",
            )
        )

    def create(self, campaign_id: uuid.UUID, **kwargs) -> CombatSession:
        session = CombatSession(campaign_id=campaign_id, **kwargs)
        self.db.add(session)
        self.db.flush()
        return session
