from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import character_service, db_session
from app.api.security import get_current_user, require_campaign_access, require_character_access
from app.database.models import User
from app.schemas.common import CharacterCreate, CharacterOut
from app.services.campaign import CharacterService

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("", response_model=CharacterOut)
def create_character(
    data: CharacterCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: CharacterService = Depends(character_service),
):
    require_campaign_access(db, data.campaign_id, user)
    try:
        return service.create(data, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[CharacterOut])
def list_characters(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: CharacterService = Depends(character_service),
):
    require_campaign_access(db, campaign_id, user)
    return service.list_for_campaign(campaign_id)


@router.get("/{character_id}", response_model=CharacterOut)
def get_character(
    character_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    _, character = require_character_access(db, character_id, user)
    return character
