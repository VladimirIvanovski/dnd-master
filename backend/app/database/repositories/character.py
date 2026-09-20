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
        self.db.info.setdefault("pending_visuals", []).append(("character", character.id))
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
        from app.game.rules import MAX_ITEM_QTY, is_unique

        if quantity < 1 or quantity > MAX_ITEM_QTY:
            raise ValueError("invalid quantity")
        existing_links = self.list_for_character(character_id)
        incoming_unique = bool((item_kwargs.get("properties") or {}).get("unique"))
        for link in existing_links:
            if link.item.name.lower() != name.lower():
                continue
            if is_unique(link.item) or incoming_unique:
                raise ValueError("unique item already owned")
            new_qty = link.quantity + quantity
            if new_qty > MAX_ITEM_QTY:
                raise ValueError("invalid quantity")
            link.quantity = new_qty
            self.db.flush()
            return link

        item = Item(campaign_id=campaign_id, name=name, **item_kwargs)
        self.db.add(item)
        self.db.flush()
        self.db.info.setdefault("pending_visuals", []).append(("item", item.id))
        durability = None
        props = item_kwargs.get("properties") or {}
        if props.get("max_durability") is not None:
            durability = int(props["max_durability"])
        link = CharacterItem(
            character_id=character_id,
            item_id=item.id,
            quantity=quantity,
            durability=durability,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def get_link(self, character_id: uuid.UUID, item_id: uuid.UUID) -> CharacterItem | None:
        return self.db.scalar(
            select(CharacterItem)
            .options(joinedload(CharacterItem.item))
            .where(
                CharacterItem.character_id == character_id,
                CharacterItem.item_id == item_id,
            )
        )

    def remove_item(self, character_id: uuid.UUID, item_id: uuid.UUID, quantity: int = 1) -> bool:
        if quantity < 1:
            raise ValueError("invalid quantity")
        link = self.get_link(character_id, item_id)
        if not link:
            return False
        if link.quantity < quantity:
            raise ValueError("insufficient quantity")
        if link.quantity == quantity:
            self.db.delete(link)
        else:
            if link.equipped:
                link.equipped = False
            link.quantity -= quantity
        self.db.flush()
        return True
