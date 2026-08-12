from uuid import UUID

from pydantic import BaseModel, Field


class NPCState(BaseModel):
    id: UUID
    name: str
    title: str = ""
    personality: str = ""
    is_alive: bool = True


class LocationState(BaseModel):
    id: UUID
    name: str
    description: str = ""
    location_type: str = "settlement"


class InventoryEntry(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    equipped: bool = False
    item_type: str = "misc"


class QuestState(BaseModel):
    id: UUID
    title: str
    description: str = ""
    status: str
    objectives: list[str] = Field(default_factory=list)


class CombatantState(BaseModel):
    id: UUID
    name: str
    combatant_type: str
    hp: int
    max_hp: int
    ac: int
    initiative: int


class CombatState(BaseModel):
    id: UUID
    status: str
    round_number: int
    combatants: list[CombatantState] = Field(default_factory=list)


class CharacterState(BaseModel):
    id: UUID
    name: str
    race: str
    class_name: str
    level: int
    xp: int
    hp: int
    max_hp: int
    ac: int
    gold: int
    silver: int = 0
    copper: int = 0
    abilities: dict[str, int]


class GameState(BaseModel):
    campaign_id: UUID
    campaign_name: str
    character: CharacterState
    current_location: LocationState | None = None
    nearby_npcs: list[NPCState] = Field(default_factory=list)
    inventory: list[InventoryEntry] = Field(default_factory=list)
    active_quests: list[QuestState] = Field(default_factory=list)
    world_state: dict = Field(default_factory=dict)
    current_time: str = "Day 1, Morning"
    weather: str = "Clear"
    combat: CombatState | None = None
