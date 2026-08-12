from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import campaign_service, db_session, gameplay_service
from app.api.security import get_current_user, require_campaign_access, require_character_access
from app.core.rate_limit import limiter
from app.database.models import User
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
    user_campaign_description: str = ""
    campaign_dna: dict = {}
    campaign_dna_version: int | None = None
    campaign_dna_summary: list[str] = []


class HistoryBeat(BaseModel):
    id: str
    event_type: str
    summary: str
    created_at: str | None = None


@router.get("/history", response_model=list[HistoryBeat])
def get_history(
    campaign_id: UUID,
    character_id: UUID,
    limit: int = 40,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: GameplayService = Depends(gameplay_service),
):
    _, character = require_character_access(db, character_id, user)
    if character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in campaign")
    limit = max(1, min(limit, 100))
    return service.scene_history(campaign_id, character_id, limit=limit)


@router.get("/state", response_model=GameState)
def get_state(
    campaign_id: UUID,
    character_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: GameplayService = Depends(gameplay_service),
    campaigns: CampaignService = Depends(campaign_service),
):
    _, character = require_character_access(db, character_id, user)
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
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    campaigns: CampaignService = Depends(campaign_service),
):
    require_campaign_access(db, campaign_id, user)
    campaign = campaigns.ensure_brief(campaign_id)
    ws = campaign.world_state or {}
    themes = ws.get("themes") or []
    if not isinstance(themes, list):
        themes = [str(themes)]
    from app.game.campaign_dna import dna_summary_lines

    dna = ws.get("campaign_dna") if isinstance(ws.get("campaign_dna"), dict) else {}
    return OpeningOut(
        tone=str(ws.get("tone") or ""),
        themes=[str(t) for t in themes],
        opening_narration=str(ws.get("opening_narration") or ""),
        opening_delivered=bool(ws.get("opening_delivered")),
        user_campaign_description=str(ws.get("user_campaign_description") or campaign.description or ""),
        campaign_dna=dna or {},
        campaign_dna_version=int(dna["version"]) if isinstance(dna, dict) and "version" in dna else None,
        campaign_dna_summary=dna_summary_lines(dna if isinstance(dna, dict) else None),
    )


@router.post("/opening/ack", response_model=OpeningOut)
def ack_opening(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    campaigns: CampaignService = Depends(campaign_service),
):
    require_campaign_access(db, campaign_id, user)
    campaign = campaigns.mark_opening_delivered(campaign_id)
    ws = campaign.world_state or {}
    themes = ws.get("themes") or []
    if not isinstance(themes, list):
        themes = [str(themes)]
    from app.game.campaign_dna import dna_summary_lines

    dna = ws.get("campaign_dna") if isinstance(ws.get("campaign_dna"), dict) else {}
    return OpeningOut(
        tone=str(ws.get("tone") or ""),
        themes=[str(t) for t in themes],
        opening_narration=str(ws.get("opening_narration") or ""),
        opening_delivered=True,
        user_campaign_description=str(ws.get("user_campaign_description") or campaign.description or ""),
        campaign_dna=dna or {},
        campaign_dna_version=int(dna["version"]) if isinstance(dna, dict) and "version" in dna else None,
        campaign_dna_summary=dna_summary_lines(dna if isinstance(dna, dict) else None),
    )


@router.post("/action", response_model=GameplayResponse)
@limiter.limit("30/minute")
def player_action(
    request: Request,
    data: PlayerActionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: GameplayService = Depends(gameplay_service),
):
    _, character = require_character_access(db, data.character_id, user)
    if character.campaign_id != data.campaign_id:
        raise HTTPException(status_code=400, detail="Character not in campaign")
    try:
        return service.handle_action(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        from app.ai.fallback_provider import LLMUnavailableError

        if isinstance(exc, LLMUnavailableError):
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        # Surface provider outages cleanly instead of raw httpx Client error text
        msg = str(exc)
        low = msg.lower()
        if any(x in low for x in ("429", "404", "rate limit", "too many requests", "cerebras", "groq")):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Cerebras and Groq are both unavailable right now "
                    "(rate limit, outage, or model not found). Please try again in a moment."
                ),
            ) from exc
        raise
