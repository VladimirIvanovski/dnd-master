from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.database.models import QuestObjective
from app.database.repositories import (
    CampaignRepository,
    CharacterRepository,
    InventoryRepository,
    LocationRepository,
    NPCRepository,
    QuestRepository,
    UserRepository,
)
from app.schemas.common import (
    CampaignCreate,
    CharacterCreate,
    InventoryItemOut,
    QuestCreate,
    QuestObjectiveOut,
    QuestOut,
)
from app.services.campaign_brief import generate_campaign_brief


class CampaignService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.campaigns = CampaignRepository(db)
        self.locations = LocationRepository(db)
        self.npcs = NPCRepository(db)

    def create(self, data: CampaignCreate):
        user = self.users.get_or_create(data.owner_username)
        campaign = self.campaigns.create(user.id, data.name, data.description)
        brief = generate_campaign_brief(data.name, data.description)
        start = self.locations.create(
            campaign.id,
            name=brief.starting_location_name[:128],
            description=brief.starting_location_description,
            location_type="settlement",
        )
        for npc in brief.starter_npcs[:3]:
            self.npcs.create(
                campaign.id,
                name=npc.name[:128],
                title=(npc.title or "")[:128],
                personality=npc.personality or "",
                goals=npc.goals or "",
                location_id=start.id,
                knowledge=npc.knowledge or [],
            )
        campaign.world_state = {
            "started": True,
            "starting_location_id": str(start.id),
            "tone": brief.tone,
            "themes": brief.themes,
            "opening_narration": brief.opening_narration,
            "opening_delivered": False,
        }
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def ensure_brief(self, campaign_id: uuid.UUID):
        """Backfill tone/opening for older campaigns missing a brief."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        ws = dict(campaign.world_state or {})
        if ws.get("tone") and ws.get("opening_narration"):
            return campaign
        brief = generate_campaign_brief(campaign.name, campaign.description or "")
        ws.update(
            {
                "tone": brief.tone,
                "themes": brief.themes,
                "opening_narration": brief.opening_narration,
                "opening_delivered": bool(ws.get("opening_delivered", False)),
            }
        )
        campaign.world_state = ws
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def mark_opening_delivered(self, campaign_id: uuid.UUID):
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        ws = dict(campaign.world_state or {})
        ws["opening_delivered"] = True
        campaign.world_state = ws
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get(self, campaign_id: uuid.UUID):
        return self.campaigns.get(campaign_id)

    def list_for_username(self, username: str):
        user = self.users.get_or_create(username)
        return self.campaigns.list_for_user(user.id)


class CharacterService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.characters = CharacterRepository(db)
        self.campaigns = CampaignRepository(db)

    def create(self, data: CharacterCreate):
        campaign = self.campaigns.get(data.campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        user = self.users.get_or_create(data.owner_username)
        con_mod = (data.constitution - 10) // 2
        max_hp = 10 + max(con_mod, 0)
        start_loc = None
        if campaign.world_state and campaign.world_state.get("starting_location_id"):
            start_loc = uuid.UUID(campaign.world_state["starting_location_id"])
        character = self.characters.create(
            user_id=user.id,
            campaign_id=data.campaign_id,
            location_id=start_loc,
            name=data.name,
            race=data.race,
            class_name=data.class_name,
            hp=max_hp,
            max_hp=max_hp,
            strength=data.strength,
            dexterity=data.dexterity,
            constitution=data.constitution,
            intelligence=data.intelligence,
            wisdom=data.wisdom,
            charisma=data.charisma,
            background=data.background,
            gold=15,
        )
        self.db.commit()
        self.db.refresh(character)
        return character

    def get(self, character_id: uuid.UUID):
        return self.characters.get(character_id)

    def list_for_campaign(self, campaign_id: uuid.UUID):
        return self.characters.list_for_campaign(campaign_id)


class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory = InventoryRepository(db)

    def list_items(self, character_id: uuid.UUID) -> list[InventoryItemOut]:
        rows = self.inventory.list_for_character(character_id)
        return [
            InventoryItemOut(
                id=row.id,
                item_id=row.item_id,
                name=row.item.name,
                quantity=row.quantity,
                equipped=row.equipped,
                item_type=row.item.item_type,
                description=row.item.description,
            )
            for row in rows
        ]


class QuestService:
    def __init__(self, db: Session):
        self.db = db
        self.quests = QuestRepository(db)

    def create(self, data: QuestCreate) -> QuestOut:
        quest = self.quests.create(
            data.campaign_id,
            title=data.title,
            description=data.description,
            character_id=data.character_id,
            reward_xp=data.reward_xp,
            reward_gold=data.reward_gold,
        )
        for i, obj in enumerate(data.objectives):
            self.db.add(QuestObjective(quest_id=quest.id, description=obj, sort_order=i))
        self.db.commit()
        quest = self.quests.get(quest.id)
        return self._to_out(quest)

    def list_active(self, campaign_id: uuid.UUID, character_id: uuid.UUID | None = None):
        return [self._to_out(q) for q in self.quests.active_for_campaign(campaign_id, character_id)]

    @staticmethod
    def _to_out(quest) -> QuestOut:
        return QuestOut(
            id=quest.id,
            title=quest.title,
            description=quest.description,
            status=quest.status,
            reward_xp=quest.reward_xp,
            reward_gold=quest.reward_gold,
            objectives=[
                QuestObjectiveOut(
                    id=o.id,
                    description=o.description,
                    is_completed=o.is_completed,
                    sort_order=o.sort_order,
                )
                for o in quest.objectives
            ],
        )
