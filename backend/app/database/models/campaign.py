import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    world_state: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_time: Mapped[str] = mapped_column(String(64), default="Day 1, Morning")
    weather: Mapped[str] = mapped_column(String(64), default="Clear")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner = relationship("User", back_populates="campaigns")
    characters = relationship("Character", back_populates="campaign")
    locations = relationship("Location", back_populates="campaign")
    npcs = relationship("NPC", back_populates="campaign")
    quests = relationship("Quest", back_populates="campaign")
    events = relationship("Event", back_populates="campaign")
    memories = relationship("Memory", back_populates="campaign")
    combat_sessions = relationship("CombatSession", back_populates="campaign")
