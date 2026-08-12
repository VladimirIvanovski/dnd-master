from __future__ import annotations

import logging

from app.ai.factory import get_llm_provider
from app.schemas.campaign_brief import CampaignBrief, StarterNpc
from app.utils.npc_variety import random_starter_npcs

logger = logging.getLogger(__name__)

BRIEF_SYSTEM = """You are establishing a D&D-style campaign bible for a persistent RPG.
Given the campaign name and description, invent a clear tone, vivid opening, and exactly ONE starter NPC.
The NPC must feel unique to THIS setting — invent an original name and role.
Do NOT reuse clichés like "Old Marta", "Innkeeper", "Village child", or "Khalid" unless the player description demands them.
Do not crowd the opening with many people — one person at the start is enough.
Opening narration must be clear and easy to visualize (not poetic fog): where the player is, what the place looks like with 2–3 concrete details, who is nearby, what is happening, then leave room to act.
Stay faithful to the player's premise. Do not invent dice rolls or mechanical rewards.
Return ONLY valid JSON for the CampaignBrief schema.
"""


def generate_campaign_brief(name: str, description: str) -> CampaignBrief:
    llm = get_llm_provider()
    prompt = f"""Campaign name: {name}
Campaign description:
{description or "(none — invent a fitting dark-fantasy hook)"}

Produce tone, themes, opening_narration, starting location, and exactly 1 starter_npc
(name, title, personality, goals, knowledge) that fits this world.
Keep the opening focused on the place and that one person — do not introduce a crowd.
"""
    try:
        brief = llm.generate_structured(prompt, CampaignBrief, system=BRIEF_SYSTEM)
        brief.starter_npcs = (brief.starter_npcs or _fallback_npcs())[:1]
        if not brief.starter_npcs:
            brief.starter_npcs = _fallback_npcs()
        return brief
    except Exception as exc:  # noqa: BLE001
        logger.warning("Campaign brief generation failed, using fallback: %s", exc)
        return CampaignBrief(
            tone="Dark fantasy adventure with grit, wonder, and lasting consequences.",
            themes=["survival", "mystery", "loyalty"],
            opening_narration=(
                f"Your story in {name} begins at the threshold of the unknown. "
                "The air is thick with promise and danger. "
                "What you do next will be remembered."
            ),
            starting_location_name="Frontier Settlement",
            starting_location_description="A rough settlement clinging to the edge of wilder lands.",
            starter_npcs=_fallback_npcs(),
        )


def _fallback_npcs() -> list[StarterNpc]:
    return [
        StarterNpc(
            name=s.name,
            title=s.title,
            personality=s.personality,
            goals=s.goals,
            knowledge=s.knowledge,
        )
        for s in random_starter_npcs(1)
    ]
