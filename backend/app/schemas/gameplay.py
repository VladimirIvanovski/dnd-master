from uuid import UUID

from pydantic import BaseModel, Field


class DialogueLine(BaseModel):
    speaker: str
    text: str


class DiceRequest(BaseModel):
    kind: str = Field(description="d20|damage|custom")
    notation: str = "1d20"
    purpose: str = ""
    skill: str | None = None
    dc: int | None = None


class ProposedEvent(BaseModel):
    event_type: str
    summary: str
    importance: int = 5
    payload: dict = Field(default_factory=dict)


class StateChange(BaseModel):
    action: str
    params: dict = Field(default_factory=dict)


class MemoryCandidate(BaseModel):
    content: str
    importance: int = 5
    entity_ids: list[str] = Field(default_factory=list)


class QuestUpdateProposal(BaseModel):
    quest_id: UUID | None = None
    title: str | None = None
    status: str | None = None
    objective_updates: list[dict] = Field(default_factory=list)
    new_quest: dict | None = None


class NPCUpdateProposal(BaseModel):
    npc_id: UUID | None = None
    name: str | None = None
    changes: dict = Field(default_factory=dict)


class DMResponse(BaseModel):
    narration: str
    dialogue: list[DialogueLine] = Field(default_factory=list)
    dice_requests: list[DiceRequest] = Field(default_factory=list)
    events: list[ProposedEvent] = Field(default_factory=list)
    state_changes: list[StateChange] = Field(default_factory=list)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list)
    quest_updates: list[QuestUpdateProposal] = Field(default_factory=list)
    npc_updates: list[NPCUpdateProposal] = Field(default_factory=list)
    # Exactly 3 short player options when possible (UI shows + custom).
    suggested_actions: list[str] = Field(default_factory=list, max_length=3)


class PlayerActionRequest(BaseModel):
    campaign_id: UUID
    character_id: UUID
    action: str = Field(min_length=1, max_length=2000)


class DiceResultOut(BaseModel):
    notation: str
    total: int
    rolls: list[int]
    purpose: str = ""
    success: bool | None = None
    ability: str | None = None
    skill: str | None = None
    modifier: int = 0
    dc: int | None = None
    natural: int | None = None
    critical: str | None = None  # natural_20 | natural_1 | None


class GameplayResponse(BaseModel):
    narration: str
    dialogue: list[DialogueLine]
    dice_results: list[DiceResultOut] = Field(default_factory=list)
    applied_events: list[str] = Field(default_factory=list)
    applied_changes: list[str] = Field(default_factory=list)
    rejected_changes: list[str] = Field(default_factory=list)
    state_snapshot: dict = Field(default_factory=dict)
    suggested_actions: list[str] = Field(default_factory=list)
