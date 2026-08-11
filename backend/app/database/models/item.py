import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    item_type: Mapped[str] = mapped_column(String(64), default="misc")
    value_gold: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[int] = mapped_column(Integer, default=0)
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    character_items = relationship("CharacterItem", back_populates="item")


class CharacterItem(Base):
    __tablename__ = "character_items"
    __table_args__ = (
        UniqueConstraint("character_id", "item_id", name="uq_character_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    equipped: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    character = relationship("Character", back_populates="inventory")
    item = relationship("Item", back_populates="character_items")
