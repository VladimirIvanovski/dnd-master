from uuid import UUID

from pydantic import BaseModel, Field


class StockEntry(BaseModel):
    name: str
    quantity: int
    price: int
    item_type: str = "misc"


class ContainerView(BaseModel):
    id: str
    name: str
    locked: bool = False


class TrapView(BaseModel):
    id: str
    name: str
    armed: bool = True


class TopicView(BaseModel):
    id: str
    label: str = ""


class NPCState(BaseModel):
    id: UUID
    name: str
    title: str = ""
    personality: str = ""
    is_alive: bool = True
    faction: str = ""
    stock: list[StockEntry] = Field(default_factory=list)
    topics: list[TopicView] = Field(default_factory=list)
    asked: list[str] = Field(default_factory=list)
    trust: float = 0
    fear: float = 0
    respect: float = 0


class LocationState(BaseModel):
    id: UUID
    name: str
    description: str = ""
    location_type: str = "settlement"
    lighting: str = "daylight"
    containers: list[ContainerView] = Field(default_factory=list)
    traps: list[TrapView] = Field(default_factory=list)


class InventoryEntry(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    equipped: bool = False
    item_type: str = "misc"
    durability: int | None = None
    weight: int = 0


class CharacterState(BaseModel):
    id: UUID
    name: str
    race: str
    class_name: str
    level: int
    xp: int
    hp: int
    max_hp: int
    temp_hp: int = 0
    ac: int
    gold: int
    silver: int = 0
    copper: int = 0
    abilities: dict[str, int]
    conditions: list[str] = Field(default_factory=list)
    stamina: int = 100
    hunger: int = 0
    thirst: int = 0
    carry_weight: int = 0
    carry_capacity: int = 150
    known_facts: list[str] = Field(default_factory=list)
    death_saves_success: int = 0
    death_saves_fail: int = 0


class QuestState(BaseModel):
    id: UUID
    title: str
    description: str = ""
    status: str
    objectives: list[str] = Field(default_factory=list)


class PlaceView(BaseModel):
    id: UUID
    name: str
    location_type: str = "settlement"
    here: bool = False


class CombatantState(BaseModel):
    id: UUID
    name: str
    combatant_type: str
    hp: int
    max_hp: int
    ac: int
    initiative: int
    cover: int = 0
    range_ft: int = 5
    x: int = 3
    y: int = 3


class CombatState(BaseModel):
    id: UUID
    status: str
    round_number: int
    whose_turn: str = ""
    can_move: bool = True
    can_strike: bool = True
    combatants: list[CombatantState] = Field(default_factory=list)


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
    factions: dict = Field(default_factory=dict)
    heard_rumors: list[str] = Field(default_factory=list)
    unheard_rumor_ids: list[str] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)
    known_locations: list[PlaceView] = Field(default_factory=list)
