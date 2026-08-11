from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class NpcSeed:
    name: str
    title: str
    personality: str
    goals: str
    knowledge: list[str]


FIRST_NAMES = [
    "Sera", "Bram", "Nima", "Torvin", "Lira", "Oren", "Yara", "Kael",
    "Mira", "Dax", "Ilya", "Rook", "Vesa", "Jori", "Ansel", "Petya",
    "Zahra", "Quill", "Hale", "Tess", "Rafi", "Eska", "Wynn", "Corin",
    "Sable", "Dune", "Fenna", "Garr", "Hadi", "Iskra",
]

SURNAMES = [
    "Ashwalker", "Reed", "Sandveil", "Ironlatch", "Moth", "Vale",
    "Cinder", "Hollow", "Brightmark", "Kestrel", "Thorn", "Mirage",
    "Salt", "Bone", "Glass", "River", "Dust", "Ember",
]

ROLES = [
    ("Caravan scout", "Wary and practical", "Keep the next caravan alive", "Bandits favor the eastern dunes."),
    ("Spice merchant", "Charming, always calculating", "Turn a profit without making enemies", "Rare saffron arrives from the south."),
    ("Well keeper", "Quiet, stubborn about fairness", "Protect the water supply", "The wells run lower each season."),
    ("Ruins guide", "Dry humor, loves old stories", "Find a lost vault before rivals do", "Lights appear over the broken pillars at dusk."),
    ("Blacksmith", "Blunt and proud of their craft", "Forge something worthy of legend", "A stranger ordered a curved blade and never returned."),
    ("Herbalist", "Soft-spoken, sharp-eyed", "Cure the fever spreading in camp", "A bitter root grows only after sandstorms."),
    ("Storyteller", "Theatrical, never fully truthful", "Earn coin and attention", "They sing of a king buried under glass."),
    ("Guard captain", "Tired, duty-bound", "Keep order without starting a riot", "Desert riders were seen near the ridge."),
    ("Cartographer", "Obsessive about details", "Map the shifting dunes", "Their last map contradicts the stars."),
    ("Camel handler", "Rough kindness for beasts first", "Keep the animals fed and calm", "Something spooked the herd last night."),
    ("Fortune reader", "Mysterious, enjoys ambiguity", "Warn of a coming omen", "They refuse to read the same palm twice."),
    ("Exiled scribe", "Bitterly precise", "Recover a stolen ledger", "Names in the ledger match missing travelers."),
    ("Glassblower", "Creative, easily distracted", "Finish a commission for a noble", "Blue glass dust is worth more than silver."),
    ("Fence", "Friendly until money is involved", "Move stolen goods quietly", "A crate marked with a serpent seal arrived today."),
    ("Pilgrim", "Earnest and travel-worn", "Reach a shrine beyond the wastes", "They claim the shrine answers only the desperate."),
]


def random_person_name(rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    if rng.random() < 0.55:
        return rng.choice(FIRST_NAMES)
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"


def random_npc_seed(rng: random.Random | None = None, *, avoid_names: set[str] | None = None) -> NpcSeed:
    rng = rng or random.Random()
    avoid = {n.lower() for n in (avoid_names or set())}
    name = random_person_name(rng)
    for _ in range(12):
        if name.lower() not in avoid:
            break
        name = random_person_name(rng)
    title, personality, goals, knowledge = rng.choice(ROLES)
    return NpcSeed(
        name=name,
        title=title,
        personality=personality,
        goals=goals,
        knowledge=[knowledge],
    )


def random_starter_npcs(count: int = 2, rng: random.Random | None = None) -> list[NpcSeed]:
    rng = rng or random.Random()
    count = max(1, min(count, 3))
    used: set[str] = set()
    out: list[NpcSeed] = []
    for _ in range(count):
        seed = random_npc_seed(rng, avoid_names=used)
        used.add(seed.name.lower())
        out.append(seed)
    return out
