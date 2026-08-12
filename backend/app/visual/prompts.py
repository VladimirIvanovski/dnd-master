from __future__ import annotations

from typing import Any


def _clip_trim(text: str, max_chars: int = 280) -> str:
    """Keep prompts short — SD-Turbo CLIP truncates past ~77 tokens."""
    t = " ".join(str(text or "").split())
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rsplit(" ", 1)[0] + "…"


class SceneVisualPromptBuilder:
    @staticmethod
    def location(data: dict[str, Any]) -> str:
        """Wide shot of where the player stands — place + concrete surroundings."""
        name = (data.get("name") or "a place")[:56]
        kind = data.get("location_type") or "place"
        biome = data.get("biome") or "fantasy countryside"
        terrain = data.get("terrain") or "paths and open ground"
        arch = data.get("architecture") or "timber and stone buildings"
        mood = data.get("atmosphere") or "lived-in, cinematic"
        weather = data.get("weather") or "clear"
        tod = data.get("time_of_day") or "day"
        style = data.get("visual_style") or "dark fantasy oil painting"
        feats = data.get("important_features") or []
        feat = ", ".join(str(f) for f in feats[:6]) if feats else (
            "foreground path, nearby structures, distant horizon"
        )
        nearby = data.get("nearby_elements") or ""
        desc = _clip_trim(data.get("description") or "", 120)

        # Grounded establishing shot: where → what you see around you → weather/light
        core = (
            f"{style} cinematic wide establishing shot from eye level, "
            f"player's current location {name} ({kind}), "
            f"clear readable place identity, "
            f"surroundings: {biome}, {terrain}, {arch}, "
            f"local details: {feat}"
        )
        if nearby:
            core += f", nearby: {_clip_trim(nearby, 80)}"
        if desc:
            core += f", scene: {desc}"
        core += (
            f", weather {weather}, time {tod}, {mood}, "
            "natural depth foreground midground background, "
            "rich materials and ground detail, volumetric light, "
            "no people faces, no text, no UI, no watermark"
        )
        return _clip_trim(core, 380)

    @staticmethod
    def npc(appearance: dict[str, Any], *, name: str = "", title: str = "") -> str:
        bits = [f"{k.replace('_', ' ')}: {v}" for k, v in appearance.items() if v][:6]
        who = f"{name}, {title}".strip(", ")
        return _clip_trim(
            f"Fantasy RPG portrait of {who or 'a character'}. "
            + "; ".join(bits)
            + ". Bust portrait, consistent face, dark fantasy, detailed skin fabric, no text.",
            300,
        )

    @staticmethod
    def character(appearance: dict[str, Any], *, name: str = "", class_name: str = "") -> str:
        bits = [f"{k.replace('_', ' ')}: {v}" for k, v in appearance.items() if v][:6]
        return _clip_trim(
            f"Fantasy RPG player portrait of {name or 'adventurer'}, {class_name or 'hero'}. "
            + "; ".join(bits)
            + ". Bust portrait, stable identity, dark fantasy, detailed armor cloth, no text.",
            300,
        )

    @staticmethod
    def item(meta: dict[str, Any], *, name: str = "") -> str:
        return _clip_trim(
            f"Game inventory icon of {name or meta.get('shape') or 'an item'}, "
            f"type {meta.get('type') or 'misc'}, material {meta.get('material') or 'simple'}, "
            f"color {meta.get('color') or 'neutral'}, centered object, simple background, "
            f"{meta.get('visual_style') or 'dark fantasy'}, high readability, no text.",
            280,
        )

    @staticmethod
    def world_map(data: dict[str, Any]) -> str:
        places = ", ".join((data.get("places") or [])[:4]) or "a lone settlement"
        name = (data.get("name") or "Unknown")[:40]
        return (
            f"fantasy parchment world map of {name}, "
            f"ink cartography mountains rivers forests roads, "
            f"regions: {places}, aged paper, ornate border, no text UI"
        )


LocationPromptBuilder = SceneVisualPromptBuilder
NPCPromptBuilder = SceneVisualPromptBuilder
CharacterPromptBuilder = SceneVisualPromptBuilder
ItemPromptBuilder = SceneVisualPromptBuilder
