import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class NPC(Base):
    __tablename__ = "npcs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(128), default="")
    personality: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="")
    fears: Mapped[str] = mapped_column(Text, default="")
    motivations: Mapped[str] = mapped_column(Text, default="")
    knowledge: Mapped[list] = mapped_column(JSONB, default=list)
    secrets: Mapped[list] = mapped_column(JSONB, default=list)
    faction: Mapped[str] = mapped_column(String(128), default="")
    is_alive: Mapped[bool] = mapped_column(default=True)
    hp: Mapped[int] = mapped_column(Integer, default=10)
    max_hp: Mapped[int] = mapped_column(Integer, default=10)
    ac: Mapped[int] = mapped_column(Integer, default=10)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    campaign = relationship("Campaign", back_populates="npcs")
    location = relationship("Location", back_populates="npcs")
    relationships = relationship("Relationship", back_populates="npc", cascade="all, delete-orphan")
