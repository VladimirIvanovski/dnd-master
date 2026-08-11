from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, quest_service
from app.api.security import require_campaign_access, resolve_username
from app.schemas.common import QuestCreate, QuestOut
from app.services.campaign import QuestService

router = APIRouter(prefix="/quests", tags=["quests"])


@router.post("", response_model=QuestOut)
def create_quest(
    data: QuestCreate,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    service: QuestService = Depends(quest_service),
):
    require_campaign_access(db, data.campaign_id, username)
    return service.create(data)


@router.get("", response_model=list[QuestOut])
def list_quests(
    campaign_id: UUID,
    character_id: UUID | None = None,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    service: QuestService = Depends(quest_service),
):
    require_campaign_access(db, campaign_id, username)
    return service.list_active(campaign_id, character_id)
