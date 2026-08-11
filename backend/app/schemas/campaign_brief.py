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
        description="Opening scene the player sees when entering the campaign (1-3 short paragraphs)"
    )
    starting_location_name: str = Field(default="Starting Settlement")
    starting_location_description: str = Field(
        default="A settlement at the edge of something larger."
    )
    starter_npcs: list[StarterNpc] = Field(
        default_factory=list,
        description="2-3 unique local NPCs with original names and roles fitting the setting",
    )
