from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, inventory_service
from app.api.security import get_current_user, require_character_access
from app.database.models import User
from app.schemas.common import InventoryItemOut
from app.services.campaign import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/{character_id}", response_model=list[InventoryItemOut])
def list_inventory(
    character_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
    service: InventoryService = Depends(inventory_service),
):
    require_character_access(db, character_id, user)
    return service.list_items(character_id)
