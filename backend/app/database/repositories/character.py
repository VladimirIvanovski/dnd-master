import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Character, CharacterItem, Item


class CharacterRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Character:
        character = Character(**kwargs)
        self.db.add(character)
        self.db.flush()
        return character

    def get(self, character_id: uuid.UUID) -> Character | None:
        return self.db.scalar(
            select(Character)
            .options(joinedload(Character.inventory).joinedload(CharacterItem.item))
            .where(Character.id == character_id)
        )

    def list_for_campaign(self, campaign_id: uuid.UUID) -> list[Character]:
        return list(
            self.db.scalars(select(Character).where(Character.campaign_id == campaign_id)).all()
        )


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_character(self, character_id: uuid.UUID) -> list[CharacterItem]:
        return list(
            self.db.scalars(
                select(CharacterItem)
                .options(joinedload(CharacterItem.item))
                .where(CharacterItem.character_id == character_id)
            ).unique().all()
        )

    def add_item(
        self,
        character_id: uuid.UUID,
        campaign_id: uuid.UUID,
        name: str,
        quantity: int = 1,
        **item_kwargs,
    ) -> CharacterItem:
        # Stack with existing inventory row of the same item name when possible.
        existing_links = self.list_for_character(character_id)
        for link in existing_links:
            if link.item.name.lower() == name.lower():
                link.quantity += quantity
                self.db.flush()
                return link

        item = Item(campaign_id=campaign_id, name=name, **item_kwargs)
        self.db.add(item)
        self.db.flush()
        link = CharacterItem(character_id=character_id, item_id=item.id, quantity=quantity)
        self.db.add(link)
        self.db.flush()
        return link

    def remove_item(self, character_id: uuid.UUID, item_id: uuid.UUID, quantity: int = 1) -> bool:
        link = self.db.scalar(
            select(CharacterItem).where(
                CharacterItem.character_id == character_id,
                CharacterItem.item_id == item_id,
            )
        )
        if not link:
            return False
        if link.quantity <= quantity:
            self.db.delete(link)
        else:
            link.quantity -= quantity
        self.db.flush()
        return True
