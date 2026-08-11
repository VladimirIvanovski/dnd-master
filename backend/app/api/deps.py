from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.campaign import (
    CampaignService,
    CharacterService,
    InventoryService,
    QuestService,
)
from app.services.gameplay import GameplayService


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def campaign_service(db: Session = Depends(db_session)) -> CampaignService:
    return CampaignService(db)


def character_service(db: Session = Depends(db_session)) -> CharacterService:
    return CharacterService(db)


def inventory_service(db: Session = Depends(db_session)) -> InventoryService:
    return InventoryService(db)


def quest_service(db: Session = Depends(db_session)) -> QuestService:
    return QuestService(db)


def gameplay_service(db: Session = Depends(db_session)) -> GameplayService:
    return GameplayService(db)
