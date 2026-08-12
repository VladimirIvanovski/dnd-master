"""Narrative / scene meta stored in campaign.world_state['narrative']."""

from __future__ import annotations

from typing import Any

from app.schemas.state import GameState

NARRATIVE_KEY = "narrative"


def get_narrative_meta(world_state: dict | None) -> dict[str, Any]:
    ws = world_state or {}
    raw = ws.get(NARRATIVE_KEY) or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "turn": int(raw.get("turn") or 0),
        "recent_event_types": list(raw.get("recent_event_types") or [])[-8:],
        "recent_event_ids": list(raw.get("recent_event_ids") or [])[-16:],
        "last_random_event_turn": int(raw.get("last_random_event_turn") or -999),
        "last_described_scene_id": raw.get("last_described_scene_id"),
        "current_scene_id": raw.get("current_scene_id"),
    }


def scene_id_for(state: GameState) -> str | None:
    loc = state.current_location
    if not loc:
        return None
    return f"{loc.id}:{loc.location_type or 'place'}"


def should_describe_environment(state: GameState, meta: dict, player_action: str) -> bool:
    """Substantial environment prose only on scene change / examine / first visit."""
    sid = scene_id_for(state)
    last = meta.get("last_described_scene_id")
    low = (player_action or "").lower()
    if any(
        w in low
        for w in (
            "look around",
            "examine",
            "inspect",
            "survey",
            "take in",
            "search the area",
            "what do i see",
            "describe",
        )
    ):
        return True
    if sid and sid != last:
        return True
    if sid and meta.get("current_scene_id") and sid != meta.get("current_scene_id"):
        return True
    return False


def environment_guidance(describe: bool, state: GameState, meta: dict) -> str:
    loc = state.current_location
    name = loc.name if loc else "this place"
    nearby = ", ".join(n.name for n in state.nearby_npcs[:4]) or "none"
    if describe:
        return (
            f"NEW/CHANGED SCENE — introduce {name} clearly so the player can picture it fast.\n"
            "Order: (1) where this is (2) 2–3 concrete atmosphere details "
            "(3) important people/objects nearby (4) what is happening now "
            "(5) leave room to act.\n"
            f"Known nearby NPCs: {nearby}. Name them if present.\n"
            "Use simple concrete language. No vague metaphor mood. "
            "About 3–6 short sentences/paragraphs, then stop."
        )
    return (
        f"Environment already established ({name}). Do NOT re-describe the whole place.\n"
        "Assume the player knows where they are. Add a concrete detail only if it changed "
        "or matters to this action. Avoid 'You are standing in…' or brochure recaps.\n"
        f"Nearby NPCs: {nearby}."
    )


def next_narrative_meta(
    meta: dict,
    *,
    state: GameState,
    described: bool,
    fired_event_id: str | None,
    fired_category: str | None,
) -> dict[str, Any]:
    turn = int(meta.get("turn") or 0) + 1
    recent_types = list(meta.get("recent_event_types") or [])
    recent_ids = list(meta.get("recent_event_ids") or [])
    last_random = int(meta.get("last_random_event_turn") or -999)
    if fired_event_id and fired_category:
        recent_types = (recent_types + [fired_category])[-8:]
        recent_ids = (recent_ids + [fired_event_id])[-16:]
        last_random = turn
    sid = scene_id_for(state)
    last_described = meta.get("last_described_scene_id")
    if described and sid:
        last_described = sid
    return {
        "turn": turn,
        "recent_event_types": recent_types,
        "recent_event_ids": recent_ids,
        "last_random_event_turn": last_random,
        "last_described_scene_id": last_described,
        "current_scene_id": sid,
    }
