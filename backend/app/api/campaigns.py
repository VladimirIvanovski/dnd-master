from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import campaign_service, db_session
from app.api.security import get_current_user, require_campaign_access
from app.core.rate_limit import limiter
from app.database.models import User
from app.schemas.common import CampaignCreate, CampaignOut
from app.services.campaign import CampaignService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignOut)
@limiter.limit("30/minute")
def create_campaign(
    request: Request,
    data: CampaignCreate,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(campaign_service),
):
    return service.create(data, owner_id=user.id)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(campaign_service),
):
    return service.list_for_user(user.id)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    _, campaign = require_campaign_access(db, campaign_id, user)
    return campaign
