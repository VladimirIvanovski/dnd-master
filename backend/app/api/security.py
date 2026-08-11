from __future__ import annotations

from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.database.repositories import CampaignRepository, CharacterRepository, UserRepository


def resolve_username(x_username: str | None = Header(default="player")) -> str:
    return (x_username or "player").strip() or "player"


def require_campaign_access(db: Session, campaign_id: UUID, username: str):
    users = UserRepository(db)
    campaigns = CampaignRepository(db)
    user = users.get_or_create(username)
    campaign = campaigns.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user, campaign


def require_character_access(db: Session, character_id: UUID, username: str):
    users = UserRepository(db)
    characters = CharacterRepository(db)
    user = users.get_or_create(username)
    character = characters.get(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user, character
