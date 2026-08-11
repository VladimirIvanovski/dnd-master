import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class CombatSession(Base):
    __tablename__ = "combat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign = relationship("Campaign", back_populates="combat_sessions")
    combatants = relationship(
        "Combatant", back_populates="session", cascade="all, delete-orphan"
    )


class Combatant(Base):
    __tablename__ = "combatants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("combat_sessions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    combatant_type: Mapped[str] = mapped_column(String(32), nullable=False)  # character|npc|enemy
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    initiative: Mapped[int] = mapped_column(Integer, default=0)
    hp: Mapped[int] = mapped_column(Integer, default=10)
    max_hp: Mapped[int] = mapped_column(Integer, default=10)
    ac: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(default=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    session = relationship("CombatSession", back_populates="combatants")
