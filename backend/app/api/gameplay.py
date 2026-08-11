from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import campaign_service, db_session, gameplay_service
from app.api.security import require_campaign_access, require_character_access, resolve_username
from app.schemas.gameplay import GameplayResponse, PlayerActionRequest
from app.schemas.state import GameState
from app.services.campaign import CampaignService
from app.services.gameplay import GameplayService

router = APIRouter(prefix="/gameplay", tags=["gameplay"])


class OpeningOut(BaseModel):
    tone: str = ""
    themes: list[str] = []
    opening_narration: str = ""
    opening_delivered: bool = False


@router.get("/state", response_model=GameState)
def get_state(
    campaign_id: UUID,
    character_id: UUID,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    service: GameplayService = Depends(gameplay_service),
    campaigns: CampaignService = Depends(campaign_service),
):
    _, character = require_character_access(db, character_id, username)
    if character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in campaign")
    try:
        campaigns.ensure_brief(campaign_id)
        return service.get_state(campaign_id, character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opening", response_model=OpeningOut)
def get_opening(
    campaign_id: UUID,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    campaigns: CampaignService = Depends(campaign_service),
):
    require_campaign_access(db, campaign_id, username)
    campaign = campaigns.ensure_brief(campaign_id)
    ws = campaign.world_state or {}
    themes = ws.get("themes") or []
    if not isinstance(themes, list):
        themes = [str(themes)]
    return OpeningOut(
        tone=str(ws.get("tone") or ""),
        themes=[str(t) for t in themes],
        opening_narration=str(ws.get("opening_narration") or ""),
        opening_delivered=bool(ws.get("opening_delivered")),
    )


@router.post("/opening/ack", response_model=OpeningOut)
def ack_opening(
    campaign_id: UUID,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    campaigns: CampaignService = Depends(campaign_service),
):
    require_campaign_access(db, campaign_id, username)
    campaign = campaigns.mark_opening_delivered(campaign_id)
    ws = campaign.world_state or {}
    themes = ws.get("themes") or []
    if not isinstance(themes, list):
        themes = [str(themes)]
    return OpeningOut(
        tone=str(ws.get("tone") or ""),
        themes=[str(t) for t in themes],
        opening_narration=str(ws.get("opening_narration") or ""),
        opening_delivered=True,
    )


@router.post("/action", response_model=GameplayResponse)
def player_action(
    data: PlayerActionRequest,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    service: GameplayService = Depends(gameplay_service),
):
    _, character = require_character_access(db, data.character_id, username)
    if character.campaign_id != data.campaign_id:
        raise HTTPException(status_code=400, detail="Character not in campaign")
    try:
        return service.handle_action(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
