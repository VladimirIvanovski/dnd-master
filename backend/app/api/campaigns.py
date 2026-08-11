from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import campaign_service, db_session
from app.api.security import require_campaign_access, resolve_username
from app.schemas.common import CampaignCreate, CampaignOut
from app.services.campaign import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignOut)
def create_campaign(
    data: CampaignCreate,
    username: str = Depends(resolve_username),
    service: CampaignService = Depends(campaign_service),
):
    data.owner_username = username
    return service.create(data)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    username: str = Depends(resolve_username),
    service: CampaignService = Depends(campaign_service),
):
    return service.list_for_username(username)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: UUID,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
):
    _, campaign = require_campaign_access(db, campaign_id, username)
    return campaign
