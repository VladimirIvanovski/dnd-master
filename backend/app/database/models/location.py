import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
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
    description: Mapped[str] = mapped_column(Text, default="")
    location_type: Mapped[str] = mapped_column(String(64), default="settlement")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    campaign = relationship("Campaign", back_populates="locations")
    characters = relationship(
        "Character", back_populates="location", foreign_keys="Character.location_id"
    )
    npcs = relationship("NPC", back_populates="location")
    parent = relationship("Location", remote_side=[id], backref="children")
