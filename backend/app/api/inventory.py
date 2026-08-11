from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import db_session, inventory_service
from app.api.security import require_character_access, resolve_username
from app.schemas.common import InventoryItemOut
from app.services.campaign import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{character_id}", response_model=list[InventoryItemOut])
def list_inventory(
    character_id: UUID,
    username: str = Depends(resolve_username),
    db: Session = Depends(db_session),
    service: InventoryService = Depends(inventory_service),
):
    require_character_access(db, character_id, username)
    return service.list_items(character_id)
