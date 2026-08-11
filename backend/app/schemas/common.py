from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    owner_username: str = "player"


class CampaignOut(ORMModel):
    id: UUID
    name: str
    description: str
    current_time: str
    weather: str
    world_state: dict
    created_at: datetime


class CharacterCreate(BaseModel):
    campaign_id: UUID
    name: str = Field(min_length=1, max_length=128)
    race: str = "Human"
    class_name: str = "Fighter"
    owner_username: str = "player"
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    background: str = ""


class CharacterOut(ORMModel):
    id: UUID
    campaign_id: UUID
    name: str
    race: str
    class_name: str
    level: int
    xp: int
    hp: int
    max_hp: int
    ac: int
    gold: int
    location_id: UUID | None
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


class InventoryItemOut(ORMModel):
    id: UUID
    item_id: UUID
    name: str
    quantity: int
    equipped: bool
    item_type: str
    description: str


class QuestObjectiveOut(ORMModel):
    id: UUID
    description: str
    is_completed: bool
    sort_order: int


class QuestOut(ORMModel):
    id: UUID
    title: str
    description: str
    status: str
    reward_xp: int
    reward_gold: int
    objectives: list[QuestObjectiveOut] = []


class QuestCreate(BaseModel):
    campaign_id: UUID
    title: str
    description: str = ""
    character_id: UUID | None = None
    reward_xp: int = 50
    reward_gold: int = 10
    objectives: list[str] = []
