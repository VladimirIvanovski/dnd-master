import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    location_type: Mapped[str] = mapped_column(String(64), default="settlement")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True, index=True
    )
    biome: Mapped[str] = mapped_column(String(128), default="")
    terrain: Mapped[str] = mapped_column(String(128), default="")
    architecture: Mapped[str] = mapped_column(String(128), default="")
    atmosphere: Mapped[str] = mapped_column(String(128), default="")
    weather: Mapped[str] = mapped_column(String(64), default="")
    time_of_day: Mapped[str] = mapped_column(String(64), default="")
    important_features: Mapped[list] = mapped_column(JSONB, default=list)
    discovered: Mapped[bool] = mapped_column(Boolean, default=True)
    coordinates: Mapped[dict] = mapped_column(JSONB, default=dict)
    visual_style: Mapped[str] = mapped_column(String(128), default="dark fantasy RPG")
    visual_prompt: Mapped[str] = mapped_column(Text, default="")
    visual_state_hash: Mapped[str] = mapped_column(String(64), default="")
    active_visual_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    campaign = relationship("Campaign", back_populates="locations")
    characters = relationship(
        "Character", back_populates="location", foreign_keys="Character.location_id"
    )
    npcs = relationship("NPC", back_populates="location")
    parent = relationship("Location", remote_side=[id], backref="children")
