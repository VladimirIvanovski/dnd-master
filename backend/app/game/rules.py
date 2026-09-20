from __future__ import annotations

from app.game.dice import ability_modifier

EXHAUSTED_CHECK_PENALTY = 2
MAX_CHECKPOINTS = 3
RESTRICTED_ITEM_TYPES = {
    "weapon",
    "weapons",
    "armor",
    "shield",
    "bow",
    "ranged",
    "crossbow",
    "thrown",
}
MAX_GOLD_GAIN = 200
MAX_ITEM_QTY = 99
MIN_CARRY = 30
STR_CARRY_MULT = 15

SLOT_FROM_TYPE = {
    "weapon": "weapon",
    "weapons": "weapon",
    "bow": "weapon",
    "ranged": "weapon",
    "crossbow": "weapon",
    "thrown": "weapon",
    "armor": "armor",
    "shield": "shield",
    "accessory": "accessory",
    "ring": "accessory",
    "cloak": "accessory",
}

DEFAULT_WEIGHT = {
    "weapon": 4,
    "armor": 12,
    "shield": 6,
    "consumable": 1,
    "potion": 1,
    "misc": 1,
}


def carry_capacity(strength: int) -> int:
    return max(MIN_CARRY, int(strength) * STR_CARRY_MULT)


def item_slot(item_type: str, properties: dict | None = None) -> str | None:
    props = properties or {}
    if props.get("slot"):
        return str(props["slot"]).lower()
    return SLOT_FROM_TYPE.get((item_type or "misc").lower())


def item_weight(item) -> int:
    weight = int(getattr(item, "weight", 0) or 0)
    if weight > 0:
        return weight
    kind = (getattr(item, "item_type", None) or "misc").lower()
    return DEFAULT_WEIGHT.get(kind, 1)


def is_unique(item) -> bool:
    props = getattr(item, "properties", None) or {}
    return bool(props.get("unique"))


def is_consumable(item) -> bool:
    kind = (getattr(item, "item_type", None) or "").lower()
    props = getattr(item, "properties", None) or {}
    return kind in {"consumable", "potion", "food", "drink"} or bool(props.get("consumable"))


def base_ac(dexterity: int) -> int:
    return 10 + ability_modifier(dexterity)


def conditions_from_extra(extra: dict | None) -> list[str]:
    raw = (extra or {}).get("conditions") or []
    out: list[str] = []
    for item in raw:
        name = str(item).strip().lower() if not isinstance(item, dict) else str(item.get("name") or "").strip().lower()
        if name and name not in out:
            out.append(name)
    return out


def extra_with_conditions(extra: dict | None, names: list[str]) -> dict:
    data = dict(extra or {})
    data["conditions"] = names
    return data


def vitals_from_extra(extra: dict | None) -> dict[str, int]:
    data = extra or {}
    return {
        "stamina": int(data.get("stamina", 100)),
        "hunger": int(data.get("hunger", 0)),
        "thirst": int(data.get("thirst", 0)),
        "exhaustion": int(data.get("exhaustion", 0)),
    }


def clamp_vitals(stamina: int, hunger: int, thirst: int, exhaustion: int) -> dict[str, int]:
    return {
        "stamina": max(0, min(100, stamina)),
        "hunger": max(0, min(100, hunger)),
        "thirst": max(0, min(100, thirst)),
        "exhaustion": max(0, min(6, exhaustion)),
    }


def tick_vitals(extra: dict | None, steps: int = 1) -> dict:
    data = dict(extra or {})
    vitals = vitals_from_extra(data)
    n = max(1, int(steps))
    vitals["hunger"] += 4 * n
    vitals["thirst"] += 6 * n
    vitals["stamina"] -= 8 * n
    clamped = clamp_vitals(**vitals)
    data.update(clamped)
    names = conditions_from_extra(data)
    worn = clamped["hunger"] >= 80 or clamped["thirst"] >= 80 or clamped["stamina"] <= 10
    if worn and "exhausted" not in names:
        names.append("exhausted")
    if not worn:
        names = [name for name in names if name != "exhausted"]
    return extra_with_conditions(data, names)


def weather_travel_ticks(weather: str | None) -> int:
    w = (weather or "").lower()
    if any(k in w for k in ("storm", "blizzard", "sandstorm")):
        return 2
    if any(k in w for k in ("rain", "snow", "heat", "scorch")):
        return 1
    return 0


def weather_check_penalty(weather: str | None) -> int:
    w = (weather or "").lower()
    if any(k in w for k in ("storm", "blizzard", "fog")):
        return 1
    return 0
