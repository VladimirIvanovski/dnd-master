import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    race: Mapped[str] = mapped_column(String(64), default="Human")
    class_name: Mapped[str] = mapped_column(String(64), default="Fighter")
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    hp: Mapped[int] = mapped_column(Integer, default=10)
    max_hp: Mapped[int] = mapped_column(Integer, default=10)
    ac: Mapped[int] = mapped_column(Integer, default=10)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    strength: Mapped[int] = mapped_column(Integer, default=10)
    dexterity: Mapped[int] = mapped_column(Integer, default=10)
    constitution: Mapped[int] = mapped_column(Integer, default=10)
    intelligence: Mapped[int] = mapped_column(Integer, default=10)
    wisdom: Mapped[int] = mapped_column(Integer, default=10)
    charisma: Mapped[int] = mapped_column(Integer, default=10)
    background: Mapped[str] = mapped_column(Text, default="")
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user = relationship("User", back_populates="characters")
    campaign = relationship("Campaign", back_populates="characters")
    location = relationship("Location", back_populates="characters", foreign_keys=[location_id])
    inventory = relationship("CharacterItem", back_populates="character", cascade="all, delete-orphan")
