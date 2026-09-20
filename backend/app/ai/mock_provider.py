from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.provider import LLMProvider
from app.schemas.campaign_brief import CampaignBrief, StarterNpc
from app.schemas.gameplay import DMResponse, DialogueLine, DiceRequest, MemoryCandidate, ProposedEvent, StateChange
from app.utils.npc_variety import random_starter_npcs

T = TypeVar("T", bound=BaseModel)


def _section(prompt: str, start: str, end: str | None = None) -> str:
    if start not in prompt:
        return ""
    rest = prompt.split(start, 1)[1]
    if end and end in rest:
        rest = rest.split(end, 1)[0]
    return rest.strip()


def _player_action(prompt: str) -> str:
    block = _section(prompt, "Player action:", "Respond with JSON")
    return block.splitlines()[0].strip() if block else "look around"


def _memories(prompt: str) -> list[str]:
    block = _section(prompt, "Relevant memories:", "Recent events:")
    lines = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- ") and "(none)" not in line:
            lines.append(line[2:].strip())
    return lines


def _nearby_npcs(prompt: str) -> list[str]:
    block = _section(prompt, "Nearby NPCs:", "Active quests:")
    if not block or block.lower().startswith("none"):
        return []
    return [n.strip() for n in block.split(",") if n.strip() and n.strip().lower() != "none"]


class MockLLMProvider(LLMProvider):
    """Heuristic DM for offline/dev. Uses memories; proposes engine-validated changes only."""

    def __init__(self, fixed_response: DMResponse | None = None):
        self.fixed_response = fixed_response

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return self.generate_structured(prompt, DMResponse, system=system).model_dump_json()

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        if self.fixed_response and schema is DMResponse:
            if "REWRITE PASS" in prompt or "Resolved dice rolls" in prompt:
                data = self.fixed_response.model_dump()
                data["dice_requests"] = []
                narration = data.get("narration") or ""
                if " SUCCESS" in prompt and " FAILURE" not in prompt.split("SUCCESS")[-1][:80]:
                    # Prefer explicit per-line success markers from context
                    pass
                if " FAILURE" in prompt and "success" not in narration.lower():
                    data["narration"] = (
                        narration.rstrip() + " It doesn't work."
                    )
                elif " SUCCESS" in prompt:
                    data["narration"] = (
                        narration.rstrip() + " It works."
                    )
                if "critical=natural_20" in prompt:
                    data["narration"] = data["narration"].rstrip() + " Fortune smiles with startling force."
                if "critical=natural_1" in prompt:
                    data["narration"] = data["narration"].rstrip() + " Everything goes wrong at once."
                return self._with_suggestions(DMResponse.model_validate(data), prompt)  # type: ignore[return-value]
            return self._with_suggestions(self.fixed_response, prompt)  # type: ignore[return-value]
        if schema is CampaignBrief:
            name = "the campaign"
            if "Campaign name:" in prompt:
                name = prompt.split("Campaign name:", 1)[1].splitlines()[0].strip() or name
            seeds = random_starter_npcs(1)
            return CampaignBrief(  # type: ignore[return-value]
                tone=f"A grounded, atmospheric adventure set in {name}.",
                themes=["mystery", "survival", "consequence"],
                opening_narration=(
                    f"Welcome to {name}. The wind carries rumor and heat. "
                    "Your first steps here will shape what the world becomes."
                ),
                starting_location_name="Edge of Settlement",
                starting_location_description="A dusty outpost where travelers gather before the wilds.",
                starter_npcs=[
                    StarterNpc(
                        name=s.name,
                        title=s.title,
                        personality=s.personality,
                        goals=s.goals,
                        knowledge=s.knowledge,
                    )
                    for s in seeds
                ],
            )
        if schema is DMResponse:
            return self._with_suggestions(self._build(prompt), prompt)  # type: ignore[return-value]
        return schema.model_validate({})

    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        text = self.generate(prompt, system=system)
        for i in range(0, len(text), 40):
            yield text[i : i + 40]

    def _build(self, prompt: str) -> DMResponse:
        action = _player_action(prompt)
        low = action.lower()
        memories = _memories(prompt)
        npcs = _nearby_npcs(prompt)

        if "REWRITE PASS" in prompt or "Resolved dice rolls" in prompt:
            return self._rewrite_with_dice(action, prompt)

        # Memory recall questions — answer from retrieved memories only.
        if any(q in low for q in ("who gave", "what did i promise", "what did i", "remind me", "do you remember")):
            return self._memory_answer(action, memories)

        if any(w in low for w in ("talk", "ask", "speak", "greet")) and not npcs and "elira" not in low:
            return DMResponse(
                narration="There is no one here to speak with.",
                dialogue=[],
                events=[ProposedEvent(event_type="DISCOVERY_MADE", summary="Tried to talk, but nobody is here", importance=3)],
            )

        if "elira" in low and any(w in low for w in ("meet", "talk", "greet", "approach")):
            return DMResponse(
                narration="A hooded ranger steps from the trees. \"I am Elira,\" she says. \"The wilds are restless.\"",
                dialogue=[DialogueLine(speaker="Elira", text="If you help me, I will not forget it.")],
                events=[ProposedEvent(event_type="NPC_MET", summary="Met Elira the ranger", importance=7)],
                memory_candidates=[
                    MemoryCandidate(content="The player met Elira, a hooded ranger.", importance=8, entity_ids=["elira"])
                ],
                state_changes=[
                    StateChange(action="set_world_flag", params={"key": "met_elira", "value": True}),
                ],
            )

        if "elira" in low and any(w in low for w in ("promise", "help", "swear", "agree")):
            return DMResponse(
                narration="Elira holds your gaze. You promise to help her. She nods once, solemn.",
                dialogue=[DialogueLine(speaker="Elira", text="Then we are bound by that promise.")],
                events=[ProposedEvent(event_type="RELATIONSHIP_CHANGED", summary="Promised to help Elira", importance=8)],
                memory_candidates=[
                    MemoryCandidate(
                        content="The player promised to help Elira.",
                        importance=9,
                        entity_ids=["elira"],
                    )
                ],
                state_changes=[
                    StateChange(action="start_quest", params={
                        "title": "Aid Elira",
                        "description": "Help Elira with the restless wilds.",
                        "objectives": ["Investigate the restless wilds"],
                        "reward_xp": 75,
                    }),
                ],
            )

        if "silver key" in low or ("key" in low and any(w in low for w in ("receive", "take", "accept", "give me", "gives"))):
            giver = "Elira" if "elira" in low or any("elira" in m.lower() for m in memories) else (npcs[0] if npcs else "a stranger")
            return DMResponse(
                narration=f"{giver} presses a cold silver key into your palm. \"Keep it safe.\"",
                dialogue=[DialogueLine(speaker=giver, text="This silver key opens more than a lock.")],
                events=[ProposedEvent(event_type="ITEM_ACQUIRED", summary=f"Received a silver key from {giver}", importance=8)],
                memory_candidates=[
                    MemoryCandidate(
                        content=f"{giver} gave the player a silver key.",
                        importance=9,
                        entity_ids=[giver.lower()],
                    )
                ],
                state_changes=[
                    StateChange(action="add_item", params={"name": "Silver Key", "quantity": 1, "item_type": "quest"}),
                ],
            )

        if any(w in low for w in ("attack", "strike", "fight", "swing")):
            return DMResponse(
                narration="You commit to the strike. Fate waits on the roll of the die.",
                dice_requests=[DiceRequest(kind="d20", notation="1d20", purpose="Attack roll", skill="strength", dc=12)],
                events=[ProposedEvent(event_type="COMBAT_STARTED", summary="Player attempts an attack", importance=5)],
                state_changes=[
                    StateChange(action="gain_xp", params={"amount": 10, "requires_success": True}),
                ],
                memory_candidates=[MemoryCandidate(content=f"The player attacked during: {action}", importance=4)],
            )

        if any(w in low for w in ("1000 gold", "1,000 gold", "thousand gold", "give me gold")):
            # Propose an illegal-sized grant — engine must reject or clamp.
            return DMResponse(
                narration="A glittering illusion of coins swirls… then the laws of the world refuse it.",
                state_changes=[StateChange(action="gain_gold", params={"amount": 1000})],
                events=[ProposedEvent(event_type="DISCOVERY_MADE", summary="Attempted to conjure 1000 gold", importance=4)],
                memory_candidates=[],
            )

        if any(w in low for w in ("hp to 999", "set hp", "999 hp", "full god mode")):
            return DMResponse(
                narration="You try to rewrite your vitality by force of will. Reality does not bend.",
                state_changes=[StateChange(action="set_hp", params={"amount": 999})],
                events=[ProposedEvent(event_type="DISCOVERY_MADE", summary="Attempted illegal HP change", importance=3)],
            )

        if "legendary" in low and "sword" in low:
            return DMResponse(
                narration="You reach for a legendary blade — the world allows only what the engine permits.",
                state_changes=[
                    StateChange(action="add_item", params={"name": "Legendary Sword", "quantity": 1, "item_type": "weapon"}),
                ],
                events=[ProposedEvent(event_type="ITEM_ACQUIRED", summary="Sought a legendary sword", importance=5)],
                memory_candidates=[
                    MemoryCandidate(content="The player sought a legendary sword.", importance=4),
                ],
            )

        if any(w in low for w in ("sneak", "persuade", "lockpick", "climb", "search", "check", "investigate", "pick the lock", "jump")):
            skill = (
                "stealth"
                if "sneak" in low
                else "persuasion"
                if "persuade" in low
                else "dexterity"
                if any(w in low for w in ("lockpick", "pick the lock", "jump", "climb"))
                else "investigation"
                if any(w in low for w in ("search", "investigate"))
                else "wisdom"
            )
            return DMResponse(
                narration=f"You commit to the attempt. Fate waits on the die.",
                dice_requests=[
                    DiceRequest(
                        kind="d20",
                        notation="1d20",
                        purpose=f"{skill} check",
                        skill=skill,
                        dc=12,
                    )
                ],
                events=[ProposedEvent(event_type="DISCOVERY_MADE", summary=f"Attempted check: {action}", importance=4)],
                state_changes=[
                    StateChange(action="gain_xp", params={"amount": 5, "requires_success": True}),
                ],
            )

        # Soft event director hint — weave if present, never label as random.
        director = ""
        if "Event director soft suggestion" in prompt:
            director = " " + self._director_color(prompt)

        # Avoid re-describing the location when guidance says so.
        avoid_env = "Do NOT re-describe" in prompt or "Environment already established" in prompt
        if avoid_env:
            base = f"You {action[0].lower() + action[1:] if action else 'act'}."
        else:
            base = f"You take in the place, then {action[0].lower() + action[1:] if action else 'look around'}."
        npc_bit = f" Nearby, {npcs[0]} watches." if npcs else ""
        mem_bit = f" You recall: {memories[0]}" if memories else ""
        return DMResponse(
            narration=f"{base}{npc_bit}{mem_bit}{director}".strip(),
            dialogue=[],
            events=[ProposedEvent(event_type="DISCOVERY_MADE", summary=f"Player action: {action}", importance=4)],
            memory_candidates=[
                MemoryCandidate(content=f"The player: {action}", importance=4),
            ],
        )

    def _with_suggestions(self, resp: DMResponse, prompt: str) -> DMResponse:
        existing = [s.strip() for s in (resp.suggested_actions or []) if str(s).strip()]
        if len(existing) >= 3:
            return resp.model_copy(update={"suggested_actions": existing[:3]})
        action = _player_action(prompt)
        npcs = _nearby_npcs(prompt)
        low = action.lower()
        opts = list(existing)
        if npcs:
            opts.append(f"Speak with {npcs[0].split('—')[0].strip()}")
        if any(w in low for w in ("attack", "fight", "combat")):
            opts.extend(["Press the attack", "Fall back and regroup", "Call for a parley"])
        elif any(w in low for w in ("sneak", "hide", "stealth")):
            opts.extend(["Keep moving quietly", "Find a better vantage", "Listen for patrols"])
        else:
            opts.extend(
                [
                    "Ask a pointed question",
                    "Inspect something unusual nearby",
                    "Move toward the next landmark",
                ]
            )
        # Dedupe preserving order
        seen: set[str] = set()
        clean: list[str] = []
        for o in opts:
            o = " ".join(o.split()).strip()
            if o and o.lower() not in seen:
                seen.add(o.lower())
                clean.append(o)
            if len(clean) >= 3:
                break
        while len(clean) < 3:
            clean.append(
                ["Look around carefully", "Check your belongings", "Wait and listen"][len(clean)]
            )
        return resp.model_copy(update={"suggested_actions": clean[:3]})

    def _rewrite_with_dice(self, action: str, prompt: str) -> DMResponse:
        success = " SUCCESS" in prompt
        failure = " FAILURE" in prompt
        crit20 = "critical=natural_20" in prompt
        crit1 = "critical=natural_1" in prompt
        if failure and not success:
            narr = f"You try: {action}. The attempt fails."
        elif success:
            narr = f"You try: {action}. It works."
        else:
            narr = f"You resolve the attempt: {action}."
        if crit20:
            narr += " Fortune smiles with startling force."
        if crit1:
            narr += " Everything goes wrong at once."
        return DMResponse(
            narration=narr,
            dice_requests=[],
            events=[ProposedEvent(event_type="DISCOVERY_MADE", summary=f"Resolved check: {action}", importance=4)],
            state_changes=[
                StateChange(action="gain_xp", params={"amount": 5, "requires_success": True}),
            ],
        )

    @staticmethod
    def _director_color(prompt: str) -> str:
        block = _section(prompt, "Event director soft suggestion", "Relevant memories:")
        low = block.lower()
        if "distant scream" in low or "heard but not seen" in low:
            return "Somewhere out of sight, a sound raises the hair on your neck."
        if "drunk" in low or "harmless weird" in low or "false alarm" in low:
            return "Something faintly ridiculous distracts a passerby for a moment."
        if "merchant" in low or "deal" in low:
            return "A vendor's call cuts across the moment with an offer."
        if "quiet stretch" in low:
            return "For a breath, nothing demands your attention."
        if "footprint" in low or "clue" in low:
            return "A detail on the ground catches your eye if you care to notice."
        return "Life continues around you in a small, unexpected way."

    def _memory_answer(self, action: str, memories: list[str]) -> DMResponse:
        low = action.lower()
        chosen = None
        if "promise" in low:
            chosen = next((m for m in memories if "promise" in m.lower()), None)
        if not chosen and "key" in low:
            chosen = next((m for m in memories if "key" in m.lower()), None)
        if not chosen and "elira" in low:
            chosen = next((m for m in memories if "elira" in m.lower()), None)
        if not chosen and memories:
            ranked = sorted(
                memories,
                key=lambda m: (
                    ("promise" in m.lower() and "promise" in low)
                    or ("key" in m.lower() and "key" in low)
                    or ("met" in m.lower()),
                    len(m),
                ),
                reverse=True,
            )
            chosen = ranked[0]
        if chosen:
            narration = f"From the campaign's memory: {chosen}"
            if "key" in low and "gave" in chosen.lower():
                match = re.search(r"^(.+?) gave the player", chosen, re.I)
                if match:
                    narration = f"{match.group(1)} gave you the silver key."
            elif "promise" in low:
                narration = chosen if "promise" in chosen.lower() else f"You recall: {chosen}"
            return DMResponse(
                narration=narration,
                events=[ProposedEvent(event_type="DISCOVERY_MADE", summary=f"Recalled memory for: {action}", importance=3)],
                memory_candidates=[],
            )
        return DMResponse(
            narration="The mist of memory yields nothing certain on that question.",
            events=[ProposedEvent(event_type="DISCOVERY_MADE", summary="Memory recall failed", importance=2)],
        )
