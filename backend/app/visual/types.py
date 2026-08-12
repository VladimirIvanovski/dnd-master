"""Asset type constants and generation profiles."""

from __future__ import annotations

WORLD_MAP = "WORLD_MAP"
LOCATION_ART = "LOCATION_ART"
ROOM_ART = "ROOM_ART"
NPC_PORTRAIT = "NPC_PORTRAIT"
CHARACTER_PORTRAIT = "CHARACTER_PORTRAIT"
ITEM_ICON = "ITEM_ICON"
ABILITY_ICON = "ABILITY_ICON"
CREATURE_PORTRAIT = "CREATURE_PORTRAIT"
COMBAT_MAP = "COMBAT_MAP"
ENVIRONMENT_ICON = "ENVIRONMENT_ICON"

ALL_ASSET_TYPES = [
    WORLD_MAP,
    LOCATION_ART,
    ROOM_ART,
    NPC_PORTRAIT,
    CHARACTER_PORTRAIT,
    ITEM_ICON,
    ABILITY_ICON,
    CREATURE_PORTRAIT,
    COMBAT_MAP,
    ENVIRONMENT_ICON,
]

# (width, height, steps) — location panel: larger + slightly more steps for surroundings detail
PROFILES: dict[str, tuple[int, int, int]] = {
    LOCATION_ART: (704, 448, 2),
    ROOM_ART: (704, 448, 2),
    NPC_PORTRAIT: (256, 256, 1),
    CHARACTER_PORTRAIT: (256, 256, 1),
    CREATURE_PORTRAIT: (256, 256, 1),
    ITEM_ICON: (128, 128, 1),
    ABILITY_ICON: (64, 64, 1),
    ENVIRONMENT_ICON: (64, 64, 1),
    WORLD_MAP: (768, 448, 1),
    COMBAT_MAP: (512, 512, 1),
}

JOB_PENDING = "PENDING"
JOB_QUEUED = "QUEUED"
JOB_GENERATING = "GENERATING"
JOB_READY = "READY"
JOB_FAILED = "FAILED"

GENERIC_ITEMS: dict[str, str] = {
    "torch": "generic_torch",
    "rope": "generic_rope",
    "potion": "generic_potion",
    "healing potion": "generic_potion",
    "sword": "generic_sword",
    "iron sword": "generic_sword",
    "shield": "generic_shield",
    "helmet": "generic_helmet",
    "coin": "generic_coin",
    "gold coin": "generic_coin",
    "key": "generic_key",
    "silver key": "generic_key",
    "scroll": "generic_scroll",
    "bread": "generic_bread",
    "gem": "generic_gem",
    "book": "generic_book",
}
