"""Recorded visual sources. Do not ship unlicensed commercial rips."""

from __future__ import annotations

CATALOG: list[dict[str, str]] = [
    {
        "id": "sd-turbo-generated",
        "category": "location/npc/item",
        "source": "local SD-Turbo",
        "license": "Stability SD-Turbo model license + campaign output policy",
        "notes": "Hashed jobs in stored_assets. IMAGE_MODEL=sd-turbo.",
    },
    {
        "id": "mock-placeholders",
        "category": "placeholder",
        "source": "IMAGE_MODEL=mock",
        "license": "internal",
        "notes": "Tests and offline. Not third-party art.",
    },
    {
        "id": "generic-item-prompts",
        "category": "item",
        "source": "visual/types.py GENERIC_ITEMS",
        "license": "internal prompts",
        "notes": "torch, sword, potion, and other generic keys.",
    },
]


def catalog_ids() -> set[str]:
    return {row["id"] for row in CATALOG}
