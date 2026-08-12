"""Lightweight Event Director — soft suggestions for the DM, not forced scripts."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.schemas.state import GameState

# Categories used for cooldown / anti-repetition.
CATEGORIES = (
    "COMBAT",
    "DANGER",
    "MYSTERY",
    "HORROR",
    "HUMOR",
    "SOCIAL",
    "DISCOVERY",
    "TREASURE",
    "TRAVEL",
    "NPC",
    "ENVIRONMENT",
    "LUCK",
    "FAILURE",
    "STRANGE",
    "QUEST",
    "WORLD_EVENT",
)


@dataclass(frozen=True)
class EventArchetype:
    id: str
    category: str
    title: str
    hint: str  # soft guidance for the LLM — weave naturally, never label as random
    weight: float = 1.0
    tags: tuple[str, ...] = ()


# Expandable library (50+). Keep hints actionable and non-formulaic.
ARCHETYPES: tuple[EventArchetype, ...] = (
    EventArchetype("distant_scream", "HORROR", "Distant scream", "A scream or cry carries from somewhere out of sight — direction unclear.", 1.0, ("night", "settlement", "wilds")),
    EventArchetype("strange_traveler", "NPC", "Strange traveler", "A traveler with odd mannerisms or gear crosses paths briefly.", 1.1, ("road", "settlement")),
    EventArchetype("lost_child", "SOCIAL", "Lost child", "A child (or someone claiming to be) seeks help — motives may be unclear.", 0.7, ("settlement")),
    EventArchetype("unusual_animal", "STRANGE", "Unusual animal", "An animal behaves strangely or appears where it shouldn't.", 1.0, ("wilds", "settlement")),
    EventArchetype("abandoned_camp", "DISCOVERY", "Abandoned camp", "Signs of a recent camp — cold ashes, prints, something left behind.", 0.9, ("wilds", "road")),
    EventArchetype("broken_wagon", "TRAVEL", "Broken wagon", "A damaged wagon or cart blocks or tempts investigation.", 0.8, ("road")),
    EventArchetype("mysterious_letter", "MYSTERY", "Mysterious letter", "A scrap of writing, letter, or note appears or is found.", 0.9, ("settlement", "indoor")),
    EventArchetype("suspicious_merchant", "SOCIAL", "Suspicious merchant", "A vendor pushes a deal that feels slightly off.", 1.0, ("settlement", "market")),
    EventArchetype("strange_footprint", "MYSTERY", "Strange footprint", "Tracks that don't match local fauna or footwear.", 1.0, ("wilds", "dungeon")),
    EventArchetype("sudden_weather", "ENVIRONMENT", "Sudden weather shift", "Weather shifts abruptly in a way that matters to the moment.", 0.9, ("outdoor")),
    EventArchetype("hidden_passage", "DISCOVERY", "Hidden passage hint", "A draft, seam, or wrong echo hints at a hidden way — do not force discovery.", 0.7, ("dungeon", "indoor")),
    EventArchetype("harmless_illusion", "STRANGE", "Harmless illusion", "A brief sensory trick that resolves as mundane or magical mischief.", 0.8, ()),
    EventArchetype("unexpected_treasure", "TREASURE", "Unexpected find", "Something small of value is findable if the player looks — don't hand it free.", 0.6, ()),
    EventArchetype("npc_argument", "SOCIAL", "NPC argument", "Two NPCs quarrel nearby; the player may ignore or intervene.", 1.0, ("settlement", "tavern")),
    EventArchetype("drunk_traveler", "HUMOR", "Drunk traveler", "A tipsy stranger causes a minor, funny complication.", 0.9, ("settlement", "tavern", "road")),
    EventArchetype("traveling_performer", "SOCIAL", "Traveling performer", "Music, a street act, or a storyteller draws a small crowd.", 0.8, ("settlement")),
    EventArchetype("injured_adventurer", "QUEST", "Injured adventurer", "A wounded traveler offers a lead, warning, or plea.", 0.9, ("road", "wilds")),
    EventArchetype("strange_statue", "MYSTERY", "Strange statue", "A statue, idol, or effigy that feels watched or wrong.", 0.8, ("dungeon", "ruin")),
    EventArchetype("unexplained_sound", "HORROR", "Unexplained sound", "A scrape, whisper, knock, or footstep with no clear source.", 1.1, ("night", "dungeon", "indoor")),
    EventArchetype("old_battlefield", "DISCOVERY", "Old battlefield remnant", "Evidence of past violence — bones, broken gear, a banner scrap.", 0.7, ("wilds", "road")),
    EventArchetype("merchant_scam", "FAILURE", "Merchant scam attempt", "Someone tries a petty con; the player can catch or fall for it.", 0.8, ("settlement", "market")),
    EventArchetype("wandering_monster", "COMBAT", "Wandering threat", "A hostile creature or brigand presence becomes possible — do not auto-start combat.", 0.7, ("wilds", "dungeon", "night")),
    EventArchetype("env_hazard", "DANGER", "Environmental hazard", "Loose stone, thin ice, smoke, tide, or similar hazard becomes relevant.", 1.0, ("wilds", "dungeon", "coast")),
    EventArchetype("strange_dream", "MYSTERY", "Strange dream echo", "If resting/quiet: a dream fragment or waking vision with symbolic weight.", 0.5, ("rest", "night")),
    EventArchetype("omen", "WORLD_EVENT", "Omen", "A small omen (birds, cracked glass, chill) that fits the campaign tone.", 0.8, ()),
    EventArchetype("false_alarm", "HUMOR", "False alarm", "Something that seems threatening resolves as harmless — relief or embarrassment.", 1.0, ()),
    EventArchetype("secret_message", "MYSTERY", "Secret message", "A coded gesture, marked coin, or whispered password in public.", 0.7, ("settlement")),
    EventArchetype("suspicious_stranger", "DANGER", "Suspicious stranger", "Someone watches the party a beat too long, then looks away.", 1.0, ("settlement", "tavern")),
    EventArchetype("unusual_smell", "ENVIRONMENT", "Unusual smell", "A smell that contradicts the scene (ozone, perfume, rot, sea far inland).", 0.9, ()),
    EventArchetype("distant_lights", "MYSTERY", "Distant lights", "Lights on a ridge, at sea, or in windows that should be dark.", 0.8, ("night", "outdoor")),
    EventArchetype("temp_opportunity", "LUCK", "Temporary opportunity", "A short-lived opening: unattended cart, open door, distracted guard.", 0.9, ()),
    EventArchetype("npc_recognizes", "NPC", "NPC recognizes player", "Someone claims to know the player — true, mistaken, or lying.", 0.7, ("settlement")),
    EventArchetype("forgotten_shrine", "DISCOVERY", "Forgotten shrine", "A small neglected shrine or offering niche.", 0.7, ("wilds", "ruin", "dungeon")),
    EventArchetype("locked_chest", "TREASURE", "Locked container", "A locked box/chest/strongbox is present if the scene allows — rewards effort.", 0.6, ("dungeon", "indoor")),
    EventArchetype("unusual_plant", "STRANGE", "Unusual plant", "Flora that shouldn't grow here, or reacts oddly to touch/light.", 0.8, ("wilds", "swamp")),
    EventArchetype("magical_phenomenon", "STRANGE", "Magical phenomenon", "A brief, local magical glitch (floating mote, reversed shadow).", 0.8, ()),
    EventArchetype("animal_odd", "STRANGE", "Animal oddity", "Birds silent, rats fleeing, a dog refusing to enter.", 1.0, ()),
    EventArchetype("mysterious_disappearance", "MYSTERY", "Mysterious disappearance", "Someone expected here is gone; a chair still warm, drink unfinished.", 0.7, ("settlement", "inn")),
    EventArchetype("unexpected_celebration", "SOCIAL", "Unexpected celebration", "A festival scrap, toast, or parade fragment spills into the street.", 0.6, ("settlement")),
    EventArchetype("local_superstition", "SOCIAL", "Local superstition", "Locals warn against a trivial-seeming act with serious belief.", 0.9, ("settlement")),
    EventArchetype("bounty_opportunity", "QUEST", "Bounty opportunity", "A posted bounty, rumor of pay, or handbill for work — optional hook.", 0.7, ("settlement", "tavern")),
    EventArchetype("rival_adventurer", "NPC", "Rival adventurer", "Another adventurer with overlapping goals appears; rivalry optional.", 0.7, ()),
    EventArchetype("strange_corpse", "HORROR", "Strange corpse", "A body or remains with one unsettling detail — keep restrained unless tone is dark.", 0.5, ("wilds", "dungeon", "alley")),
    EventArchetype("broken_bridge", "TRAVEL", "Broken bridge / blocked path", "A path forward is impaired; alternatives exist.", 0.8, ("road", "wilds")),
    EventArchetype("weather_hazard", "DANGER", "Weather hazard", "Fog, ice, dust, or storm creates risk or cover.", 0.9, ("outdoor")),
    EventArchetype("traveling_caravan", "TRAVEL", "Traveling caravan", "A caravan offers trade, rumor, or temporary travel company.", 0.8, ("road")),
    EventArchetype("map_fragment", "DISCOVERY", "Old map fragment", "A torn map scrap with a partial mark — not a full quest dump.", 0.6, ()),
    EventArchetype("hidden_clue", "DISCOVERY", "Hidden clue", "A detail that rewards careful observation related to a nearby hook.", 0.9, ()),
    EventArchetype("strange_child_question", "STRANGE", "Strange child question", "A child asks an oddly specific or knowing question.", 0.6, ("settlement")),
    EventArchetype("npc_deal", "SOCIAL", "NPC offering a deal", "An NPC proposes a trade, favor, or bargain with a clear cost.", 1.0, ("settlement", "tavern")),
    EventArchetype("unexplained_magic", "STRANGE", "Unexplained magical effect", "A small effect with no caster in sight (door unlocks, candle flares blue).", 0.8, ()),
    EventArchetype("quiet_stretch", "ENVIRONMENT", "Quiet stretch", "Nothing major — a beat of atmosphere or mundane life. Prefer brevity.", 1.4, ()),
    EventArchetype("previous_choice_echo", "WORLD_EVENT", "Previous choice echoes", "A consequence or rumor tied to something the player already did.", 0.9, ("memory")),
    EventArchetype("npc_remembers", "NPC", "NPC remembers", "An NPC recalls a prior interaction and reacts accordingly.", 0.9, ("memory", "npc")),
    EventArchetype("misleading_rumor", "FAILURE", "Misleading information", "Someone gives partial or wrong info that sounds plausible.", 0.8, ("settlement", "tavern")),
    EventArchetype("ambush_hint", "COMBAT", "Ambush tension", "Signs of an ambush forming — give the player a chance to notice or act.", 0.6, ("wilds", "road", "night")),
    EventArchetype("harmless_weird", "HUMOR", "Harmless weird event", "Something odd and funny that doesn't threaten anyone.", 1.0, ()),
    EventArchetype("difficult_choice", "QUEST", "Difficult choice seed", "Present a fork with real tradeoffs if it fits; never force a menu.", 0.7, ()),
    EventArchetype("unrelated_slice", "WORLD_EVENT", "Unrelated world slice", "A vignette unrelated to the main quest that makes the world feel alive.", 1.0, ()),
    EventArchetype("heard_not_seen", "HORROR", "Heard but not seen", "The player hears something they cannot see yet.", 1.0, ("night", "dungeon")),
)


@dataclass
class EventSuggestion:
    archetype: EventArchetype | None
    fire: bool
    reason: str
    cooldown_turns: int = 2


def _loc_tags(state: GameState) -> set[str]:
    tags: set[str] = set()
    loc = state.current_location
    if not loc:
        return tags
    lt = (loc.location_type or "").lower()
    name = (loc.name or "").lower()
    tags.add(lt)
    if lt in {"settlement", "town", "city", "village", "outpost"}:
        tags.update({"settlement", "outdoor"})
    if lt in {"dungeon", "ruin", "cave"}:
        tags.update({"dungeon", "indoor"})
    if lt in {"wilderness", "forest", "road", "coast", "swamp"}:
        tags.update({"wilds", "outdoor"})
    if "tavern" in name or "inn" in name:
        tags.update({"tavern", "indoor", "settlement"})
    if "market" in name:
        tags.add("market")
    time = (state.current_time or "").lower()
    if "night" in time or "evening" in time:
        tags.add("night")
    if "morning" in time or "dawn" in time:
        tags.add("day")
    if state.nearby_npcs:
        tags.add("npc")
    return tags


class EventDirector:
    """Weighted, cooldown-aware soft suggestions for the DM prompt."""

    def __init__(
        self,
        archetypes: Sequence[EventArchetype] = ARCHETYPES,
        *,
        rng: random.Random | None = None,
        base_chance: float = 0.28,
        cooldown_turns: int = 2,
    ):
        self.archetypes = list(archetypes)
        self.rng = rng or random.Random()
        self.base_chance = base_chance
        self.cooldown_turns = cooldown_turns

    def suggest(
        self,
        state: GameState,
        *,
        player_action: str,
        narrative_meta: dict,
    ) -> EventSuggestion:
        turn = int(narrative_meta.get("turn") or 0)
        last = int(narrative_meta.get("last_random_event_turn") or -999)
        recent_cats = [str(c) for c in (narrative_meta.get("recent_event_types") or [])][-6:]
        recent_ids = [str(i) for i in (narrative_meta.get("recent_event_ids") or [])][-12:]

        # Priority: player action / combat / dialogue — usually no random event.
        if state.combat:
            return EventSuggestion(None, False, "combat_active", self.cooldown_turns)
        low = (player_action or "").lower()
        if any(w in low for w in ("say ", "ask ", "tell ", "talk", "persuade", "convince")):
            if self.rng.random() > 0.12:
                return EventSuggestion(None, False, "active_dialogue", self.cooldown_turns)
        if turn - last < self.cooldown_turns:
            return EventSuggestion(None, False, "cooldown", self.cooldown_turns)

        chance = self._chance(state, player_action, turn, last)
        if self.rng.random() > chance:
            return EventSuggestion(None, False, "no_fire", self.cooldown_turns)

        loc_tags = _loc_tags(state)
        candidates: list[tuple[float, EventArchetype]] = []
        for arch in self.archetypes:
            if arch.id in recent_ids:
                continue
            if arch.category in recent_cats[-2:]:
                continue
            w = arch.weight
            if arch.tags and loc_tags:
                overlap = len(set(arch.tags) & loc_tags)
                if overlap:
                    w *= 1.0 + 0.35 * overlap
                elif arch.tags and not (set(arch.tags) & {"memory"}):
                    # Mildly downweight poorly fitting tags
                    if not any(t in loc_tags for t in arch.tags):
                        w *= 0.55
            if arch.category == "COMBAT" and state.character.level <= 1:
                w *= 0.5
            if "quiet" in arch.id and chance < 0.35:
                w *= 1.3
            candidates.append((max(0.05, w), arch))

        if not candidates:
            return EventSuggestion(None, False, "no_candidates", self.cooldown_turns)

        total = sum(w for w, _ in candidates)
        pick = self.rng.uniform(0, total)
        upto = 0.0
        chosen = candidates[-1][1]
        for w, arch in candidates:
            upto += w
            if pick <= upto:
                chosen = arch
                break
        return EventSuggestion(chosen, True, "selected", self.cooldown_turns)

    def _chance(self, state: GameState, player_action: str, turn: int, last: int) -> float:
        chance = self.base_chance
        low = (player_action or "").lower()
        loc = state.current_location
        lt = (loc.location_type or "").lower() if loc else ""

        if any(w in low for w in ("travel", "walk to", "go to", "head to", "journey", "follow the road")):
            chance += 0.18
        if any(w in low for w in ("wait", "rest", "camp", "sleep", "look around", "listen")):
            chance += 0.1
        if lt in {"wilderness", "dungeon", "ruin", "cave", "road"}:
            chance += 0.12
        if lt in {"settlement", "town", "city", "village"}:
            chance -= 0.05
        if "danger" in (state.weather or "").lower() or "storm" in (state.weather or "").lower():
            chance += 0.08
        # After a long quiet stretch, nudge upward
        if turn - last >= 5:
            chance += 0.12
        return max(0.05, min(1.0, chance))


def format_suggestion_for_prompt(suggestion: EventSuggestion) -> str:
    if not suggestion.fire or not suggestion.archetype:
        return (
            "Event director: no random beat this turn. Focus on the player's action. "
            "Vary pacing; quiet is fine."
        )
    a = suggestion.archetype
    return (
        f"Event director soft suggestion (optional — weave naturally if it fits; "
        f"NEVER say 'random event'; skip if it would derail combat/dialogue/quest climax):\n"
        f"- id={a.id} category={a.category} title={a.title}\n"
        f"- beat: {a.hint}"
    )
