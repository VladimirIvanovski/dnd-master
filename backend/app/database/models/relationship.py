import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.ids import new_uuid, utcnow


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint("character_id", "npc_id", name="uq_character_npc_rel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False, index=True
    )
    npc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("npcs.id"), nullable=False, index=True
    )
    trust: Mapped[float] = mapped_column(Float, default=0.0)
    fear: Mapped[float] = mapped_column(Float, default=0.0)
    respect: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    npc = relationship("NPC", back_populates="relationships")
