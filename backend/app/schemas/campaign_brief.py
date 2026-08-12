from pydantic import BaseModel, Field


class StarterNpc(BaseModel):
    name: str
    title: str = ""
    personality: str = ""
    goals: str = ""
    knowledge: list[str] = Field(default_factory=list)


class CampaignBrief(BaseModel):
    """LLM-authored campaign tone and opening — stored in world_state."""

    tone: str = Field(description="1-2 sentences describing mood, genre, and stakes")
    themes: list[str] = Field(default_factory=list, description="3-5 short theme tags")
    opening_narration: str = Field(
        description=(
            "Clear opening scene (3–6 short sentences/paragraphs): where the player is, "
            "concrete look/atmosphere, who/what is nearby, what is happening now, then room to act. "
            "Simple language — not poetic vagueness."
        )
    )
    starting_location_name: str = Field(default="Starting Settlement")
    starting_location_description: str = Field(
        default="A settlement at the edge of something larger."
    )
    starter_npcs: list[StarterNpc] = Field(
        default_factory=list,
        description="Exactly 1 unique local NPC with an original name and role fitting the setting",
    )
