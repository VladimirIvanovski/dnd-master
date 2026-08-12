"""Persistent Campaign DNA — creative identity selected once at campaign creation."""

from __future__ import annotations

import random
import re
from typing import Any

DNA_VERSION = 1

# Predefined option lists (expandable).
CORE_THEME = [
    "heroic adventure",
    "glory",
    "survival",
    "redemption",
    "revenge",
    "discovery",
    "war",
    "political intrigue",
    "exploration",
    "friendship",
    "sacrifice",
    "treasure hunting",
]

TONE = [
    "hopeful",
    "epic",
    "gritty",
    "lighthearted",
    "tragic",
    "mysterious",
    "whimsical",
    "dark",
    "romantic",
    "adventurous",
]

HERO_STYLE = [
    "unlikely heroes",
    "legendary heroes",
    "reluctant heroes",
    "outcasts",
    "mercenaries",
    "chosen heroes",
    "ordinary people becoming heroes",
]

WORLD_FLAVOR = [
    "ancient kingdoms",
    "frontier settlements",
    "floating islands",
    "desert empires",
    "frozen kingdoms",
    "coastal cities",
    "jungle civilizations",
    "underground kingdoms",
    "dragon territories",
    "haunted borderlands",
    "merchant republics",
    "ruined empires reclaiming the wild",
]

MAGIC_STYLE = [
    "rare and mysterious",
    "common and practical",
    "ancient",
    "dangerous",
    "elemental",
    "divine",
    "corrupted",
    "wild",
    "technological-magical",
]

CONFLICT_STYLE = [
    "personal rivalries",
    "faction warfare",
    "moral dilemmas",
    "resource scarcity",
    "hidden conspiracies",
    "monstrous threats",
    "political coups",
    "cursed bargains",
    "honor duels and reputation",
]

EXPLORATION_STYLE = [
    "landmark hopping",
    "dungeon delving",
    "wilderness survival treks",
    "urban intrigue routes",
    "sea voyages",
    "ruin archaeology",
    "map-revealing discovery",
    "secret passages and vertical cities",
]

NPC_STYLE = [
    "warm and memorable",
    "suspicious and guarded",
    "theatrical and larger-than-life",
    "quiet with hidden depths",
    "pragmatic traders",
    "honor-bound warriors",
    "whimsical eccentrics",
    "tragic survivors",
]

COMBAT_STYLE = [
    "cinematic and heroic",
    "brutal and costly",
    "tactical and terrain-focused",
    "rare but decisive",
    "skirmish-heavy",
    "duels and set-pieces",
    "monster-hunt spectacle",
]

HUMOR_LEVEL = [
    "almost none",
    "dry wit",
    "occasional levity",
    "frequent lighthearted beats",
    "slapstick-friendly",
]

HORROR_LEVEL = [
    "none",
    "subtle unease",
    "folk-horror hints",
    "occasional dread",
    "frequent darkness",
]

MYSTERY_LEVEL = [
    "low — straightforward stakes",
    "moderate — secrets unfold gradually",
    "high — layered enigmas",
    "constant — everything has a second meaning",
]

ADVENTURE_LEVEL = [
    "calm stretches with spikes of danger",
    "steady momentum",
    "high-octane set pieces",
    "episodic quests",
    "escalating grand journey",
]

SPECIAL_MOTIFS = [
    "lanterns and guiding lights",
    "storms and changing weather",
    "masks and hidden faces",
    "songs and oral legends",
    "broken oaths",
    "maps and missing pages",
    "rival adventuring companies",
    "sacred animals",
    "ancient coins",
    "mirrors and reflections",
    "bridges and crossings",
    "feasts and hospitality rites",
    "embers and dying fires",
    "bells and signal towers",
    "tattoos and brands of belonging",
]

RECURRING_VISUAL_THEMES = [
    "gold light on wet stone",
    "salt-stained wood and rope",
    "crimson banners in fog",
    "moss on carved ruins",
    "desert glare and indigo shadows",
    "snow lit by aurora",
    "bioluminescent caves",
    "stained glass and candle smoke",
    "iron and rusted mail",
    "flowering vines over broken walls",
    "harbor lanterns on black water",
    "ash falling like snow",
]

# Category key -> option list (single-value unless noted)
SINGLE_CATEGORIES: dict[str, list[str]] = {
    "core_theme": CORE_THEME,
    "tone": TONE,
    "hero_style": HERO_STYLE,
    "world_flavor": WORLD_FLAVOR,
    "magic_style": MAGIC_STYLE,
    "conflict_style": CONFLICT_STYLE,
    "exploration_style": EXPLORATION_STYLE,
    "npc_style": NPC_STYLE,
    "combat_style": COMBAT_STYLE,
    "humor_level": HUMOR_LEVEL,
    "horror_level": HORROR_LEVEL,
    "mystery_level": MYSTERY_LEVEL,
    "adventure_level": ADVENTURE_LEVEL,
}

MULTI_CATEGORIES: dict[str, list[str]] = {
    "special_motifs": SPECIAL_MOTIFS,
    "recurring_visual_themes": RECURRING_VISUAL_THEMES,
}

# Keywords in user description -> preferred DNA values (first match wins per category).
_KEYWORD_OVERRIDES: list[tuple[str, dict[str, Any]]] = [
    (r"\bglory|tournament|renown|legend\b", {"core_theme": "glory", "conflict_style": "honor duels and reputation"}),
    (r"\bsurviv|harsh|scarce|starv\b", {"core_theme": "survival", "conflict_style": "resource scarcity", "horror_level": "folk-horror hints"}),
    (r"\brevenge|vengeance\b", {"core_theme": "revenge", "tone": "gritty"}),
    (r"\bredeem|redemption\b", {"core_theme": "redemption", "tone": "hopeful"}),
    (r"\bwar|siege|battlefield\b", {"core_theme": "war", "combat_style": "brutal and costly"}),
    (r"\bintrigue|politic|court\b", {"core_theme": "political intrigue", "exploration_style": "urban intrigue routes"}),
    (r"\bmystery|secret|enigma\b", {"mystery_level": "high — layered enigmas", "tone": "mysterious"}),
    (r"\bhorror|dread|nightmare\b", {"horror_level": "frequent darkness", "tone": "dark"}),
    (r"\bwhimsy|fairy|fey|lighthearted|comedy\b", {"tone": "whimsical", "humor_level": "frequent lighthearted beats"}),
    (r"\bgritty|grim\b", {"tone": "gritty", "combat_style": "brutal and costly"}),
    (r"\bepic|grand\b", {"tone": "epic", "adventure_level": "escalating grand journey"}),
    (r"\bhope|bright\b", {"tone": "hopeful"}),
    (r"\bdesert\b", {"world_flavor": "desert empires"}),
    (r"\bfrozen|ice|winter|arctic\b", {"world_flavor": "frozen kingdoms"}),
    (r"\bjungle|rainforest\b", {"world_flavor": "jungle civilizations"}),
    (r"\bcoast|harbor|sea|pirate\b", {"world_flavor": "coastal cities", "exploration_style": "sea voyages"}),
    (r"\bunderdark|underground|dwarf.*deep\b", {"world_flavor": "underground kingdoms"}),
    (r"\bdragon\b", {"world_flavor": "dragon territories"}),
    (r"\bfloating island\b", {"world_flavor": "floating islands"}),
    (r"\bfrontier|outpost|border\b", {"world_flavor": "frontier settlements"}),
    (r"\bmagic.?rare|rare magic\b", {"magic_style": "rare and mysterious"}),
    (r"\bwild magic|chaos magic\b", {"magic_style": "wild"}),
    (r"\bdivine|gods?\b", {"magic_style": "divine"}),
    (r"\bcorrupt|blight\b", {"magic_style": "corrupted"}),
    (r"\bmercenar", {"hero_style": "mercenaries"}),
    (r"\boutcast|exile\b", {"hero_style": "outcasts"}),
    (r"\breluctant\b", {"hero_style": "reluctant heroes"}),
    (r"\bchosen one|prophec\b", {"hero_style": "chosen heroes"}),
    (r"\btreasure|gold rush\b", {"core_theme": "treasure hunting"}),
    (r"\bexplor\b", {"core_theme": "exploration", "exploration_style": "map-revealing discovery"}),
]


def generate_random_dna(rng: random.Random | None = None) -> dict[str, Any]:
    rng = rng or random.Random()
    dna: dict[str, Any] = {"version": DNA_VERSION}
    for key, options in SINGLE_CATEGORIES.items():
        dna[key] = rng.choice(options)
    for key, options in MULTI_CATEGORIES.items():
        k = min(3, len(options))
        dna[key] = rng.sample(options, k=k)
    return dna


def merge_user_description_into_dna(
    dna: dict[str, Any],
    user_description: str,
    *,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """User description overrides conflicting DNA; unspecified categories keep random picks."""
    rng = rng or random.Random()
    out = dict(dna)
    out["version"] = DNA_VERSION
    text = (user_description or "").strip()
    if not text:
        return out

    low = text.lower()
    for pattern, overrides in _KEYWORD_OVERRIDES:
        if re.search(pattern, low, re.I):
            for cat, value in overrides.items():
                out[cat] = value

    # Soft motif boost from description words
    motif_hits = [m for m in SPECIAL_MOTIFS if any(w in low for w in m.lower().split()[:2])]
    if motif_hits:
        current = list(out.get("special_motifs") or [])
        for m in motif_hits[:2]:
            if m not in current:
                current.insert(0, m)
        out["special_motifs"] = current[:3]

    # Ensure multi fields are lists
    for key in MULTI_CATEGORIES:
        val = out.get(key)
        if isinstance(val, str):
            out[key] = [val]
        elif not isinstance(val, list) or not val:
            out[key] = rng.sample(MULTI_CATEGORIES[key], k=2)

    return out


def build_campaign_dna(
    user_description: str = "",
    *,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    rng = rng or random.Random()
    dna = generate_random_dna(rng)
    return merge_user_description_into_dna(dna, user_description, rng=rng)


def format_dna_for_prompt(
    dna: dict[str, Any] | None,
    user_description: str = "",
) -> str:
    if not dna:
        return ""
    lines = [
        "Campaign DNA (creative identity — constraint, NOT a rigid script):",
        f"- version: {dna.get('version', DNA_VERSION)}",
    ]
    desc = (user_description or "").strip()
    if desc:
        lines.append(
            f"- USER CAMPAIGN DESCRIPTION (highest priority over DNA): {desc[:800]}"
        )
    lines.append(
        "Priority: player action & established world > user description > Campaign DNA > generic DM style."
    )
    lines.append("Use DNA to color opportunities when natural; do NOT force the theme into every response.")
    for key in SINGLE_CATEGORIES:
        if key in dna:
            lines.append(f"- {key}: {dna[key]}")
    for key in MULTI_CATEGORIES:
        val = dna.get(key) or []
        if isinstance(val, list):
            lines.append(f"- {key}: {', '.join(str(v) for v in val)}")
        elif val:
            lines.append(f"- {key}: {val}")
    # Theme guidance hint
    theme = str(dna.get("core_theme") or "")
    if theme:
        lines.append(f"- creative lean: when appropriate, open doors related to '{theme}' without railroading.")
    return "\n".join(lines)


def dna_summary_lines(dna: dict[str, Any] | None) -> list[str]:
    if not dna:
        return []
    bits = []
    for key in (
        "core_theme",
        "tone",
        "hero_style",
        "world_flavor",
        "magic_style",
        "conflict_style",
        "combat_style",
        "humor_level",
        "horror_level",
        "mystery_level",
    ):
        if dna.get(key):
            bits.append(f"{key.replace('_', ' ')}: {dna[key]}")
    motifs = dna.get("special_motifs") or []
    if motifs:
        bits.append("motifs: " + ", ".join(str(m) for m in motifs[:3]))
    return bits
