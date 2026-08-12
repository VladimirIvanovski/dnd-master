from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.database.models import User
from app.database.repositories import CampaignRepository, CharacterRepository, UserRepository
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(db_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def user_from_token(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_campaign_access(db: Session, campaign_id: UUID, user: User):
    campaigns = CampaignRepository(db)
    campaign = campaigns.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user, campaign


def require_character_access(db: Session, character_id: UUID, user: User):
    characters = CharacterRepository(db)
    character = characters.get(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    campaign = CampaignRepository(db).get(character.campaign_id)
    if not campaign or campaign.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user, character
