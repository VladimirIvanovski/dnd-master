"""Engine helpers for stock, knowledge, containers, factions, combat extras."""

from __future__ import annotations


def known_facts(extra: dict | None) -> list[str]:
    out: list[str] = []
    for item in (extra or {}).get("known_facts") or []:
        text = str(item).strip()
        if text and text not in out:
            out.append(text)
    return out


def add_fact(extra: dict | None, fact: str) -> dict:
    data = dict(extra or {})
    facts = known_facts(data)
    text = str(fact).strip()
    if text and text not in facts:
        facts.append(text)
    data["known_facts"] = facts[:40]
    return data


def resist_multiplier(extra: dict | None, damage_type: str | None) -> float:
    if not damage_type:
        return 1.0
    raw = (extra or {}).get("resistances") or {}
    if not isinstance(raw, dict):
        return 1.0
    val = raw.get(str(damage_type).lower())
    if val is None:
        return 1.0
    return max(0.0, min(1.0, float(val)))


def apply_resistance(amount: int, extra: dict | None, damage_type: str | None) -> int:
    return int(max(0, amount) * resist_multiplier(extra, damage_type) + 1e-9)


def death_saves(extra: dict | None) -> dict[str, int]:
    raw = (extra or {}).get("death_saves") or {}
    return {
        "success": max(0, min(3, int(raw.get("success", 0) or 0))),
        "fail": max(0, min(3, int(raw.get("fail", 0) or 0))),
    }


def record_death_save(extra: dict | None, *, success: bool) -> tuple[dict, str]:
    data = dict(extra or {})
    ds = death_saves(data)
    if success:
        ds["success"] = min(3, ds["success"] + 1)
    else:
        ds["fail"] = min(3, ds["fail"] + 1)
    data["death_saves"] = ds
    if ds["fail"] >= 3:
        return data, "dead"
    if ds["success"] >= 3:
        return data, "stable"
    return data, "ongoing"


def reset_death_saves(extra: dict | None) -> dict:
    data = dict(extra or {})
    data["death_saves"] = {"success": 0, "fail": 0}
    return data


def normalize_stock(raw) -> list[dict]:
    out: list[dict] = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        qty = int(row.get("quantity") or 0)
        if not name or qty < 1:
            continue
        out.append(
            {
                "name": name,
                "quantity": min(99, qty),
                "price": max(0, int(row.get("price") or 0)),
                "item_type": str(row.get("item_type") or "misc"),
            }
        )
    return out


def take_from_stock(extra: dict | None, name: str, qty: int) -> tuple[dict, dict]:
    extra = dict(extra or {})
    stock = normalize_stock(extra.get("stock"))
    key = str(name).strip().lower()
    found = next((row for row in stock if row["name"].lower() == key), None)
    if not found:
        raise ValueError("merchant does not sell that")
    if found["quantity"] < qty:
        raise ValueError("out of stock")
    found["quantity"] -= qty
    extra["stock"] = [row for row in stock if row["quantity"] > 0]
    extra["gold"] = int(extra.get("gold") or 0) + found["price"] * qty
    return extra, found


def add_to_stock(
    extra: dict | None, name: str, qty: int, price: int, item_type: str = "misc"
) -> dict:
    extra = dict(extra or {})
    gold = int(extra.get("gold") or 0)
    cost = max(0, price) * qty
    if gold < cost:
        raise ValueError("merchant cannot afford that")
    extra["gold"] = gold - cost
    stock = normalize_stock(extra.get("stock"))
    key = str(name).strip().lower()
    for row in stock:
        if row["name"].lower() == key:
            row["quantity"] = min(99, row["quantity"] + qty)
            extra["stock"] = stock
            return extra
    stock.append(
        {
            "name": str(name).strip(),
            "quantity": qty,
            "price": max(0, price),
            "item_type": item_type or "misc",
        }
    )
    extra["stock"] = stock
    return extra


def lighting_of(extra: dict | None) -> str:
    value = str((extra or {}).get("lighting") or "daylight").strip().lower()
    return value or "daylight"


def public_containers(extra: dict | None) -> list[dict]:
    out: list[dict] = []
    for box in (extra or {}).get("containers") or []:
        if not isinstance(box, dict):
            continue
        cid = str(box.get("id") or "").strip()
        name = str(box.get("name") or "").strip()
        if not cid or not name:
            continue
        out.append({"id": cid, "name": name, "locked": bool(box.get("locked"))})
    return out


def loot_container(extra: dict | None, container_id: str) -> tuple[dict, list[dict]]:
    extra = dict(extra or {})
    boxes = list(extra.get("containers") or [])
    for box in boxes:
        if not isinstance(box, dict) or str(box.get("id")) != str(container_id):
            continue
        if box.get("locked"):
            raise ValueError("container is locked")
        items = [item for item in (box.get("items") or []) if isinstance(item, dict)]
        box["items"] = []
        extra["containers"] = boxes
        return extra, items
    raise ValueError("container not found")


def unlock_container(extra: dict | None, container_id: str) -> dict:
    extra = dict(extra or {})
    boxes = list(extra.get("containers") or [])
    for box in boxes:
        if isinstance(box, dict) and str(box.get("id")) == str(container_id):
            box["locked"] = False
            extra["containers"] = boxes
            return extra
    raise ValueError("container not found")


def scheduled_location(extra: dict | None, period_label: str) -> str | None:
    sched = (extra or {}).get("schedule") or {}
    if not isinstance(sched, dict):
        return None
    raw = sched.get(period_label) or sched.get(str(period_label).lower())
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def cover_bonus(extra: dict | None) -> int:
    value = int((extra or {}).get("cover") or 0)
    return value if value in (0, 2, 5) else 0


def range_ft(extra: dict | None) -> int:
    return max(0, int((extra or {}).get("range_ft") or 5))


def faction_delta(world_state: dict | None, faction: str, delta: int) -> dict:
    name = str(faction).strip()
    if not name:
        raise ValueError("faction required")
    ws = dict(world_state or {})
    factions = dict(ws.get("factions") or {})
    row = dict(factions.get(name) or {"player_rep": 0})
    row["player_rep"] = max(-100, min(100, int(row.get("player_rep") or 0) + int(delta)))
    factions[name] = row
    ws["factions"] = factions
    return ws


def _trap_rows(extra: dict | None) -> list[dict]:
    rows = []
    for trap in (extra or {}).get("traps") or []:
        if isinstance(trap, dict) and str(trap.get("id") or "").strip():
            rows.append(trap)
    return rows


def public_traps(extra: dict | None) -> list[dict]:
    out: list[dict] = []
    for trap in _trap_rows(extra):
        if not trap.get("spotted"):
            continue
        out.append(
            {
                "id": str(trap["id"]),
                "name": str(trap.get("name") or "Trap"),
                "armed": bool(trap.get("armed", True)),
            }
        )
    return out


def first_armed_trap_id(extra: dict | None) -> str | None:
    for trap in _trap_rows(extra):
        if trap.get("armed", True):
            return str(trap["id"])
    return None


def _mutate_trap(extra: dict | None, trap_id: str) -> tuple[dict, dict]:
    extra = dict(extra or {})
    traps = list(extra.get("traps") or [])
    for trap in traps:
        if isinstance(trap, dict) and str(trap.get("id")) == str(trap_id):
            extra["traps"] = traps
            return extra, trap
    raise ValueError("trap not found")


def spot_trap(extra: dict | None, trap_id: str) -> dict:
    extra, trap = _mutate_trap(extra, trap_id)
    trap["spotted"] = True
    return extra


def disarm_trap(extra: dict | None, trap_id: str) -> dict:
    extra, trap = _mutate_trap(extra, trap_id)
    if not trap.get("spotted"):
        raise ValueError("trap not spotted")
    if not trap.get("armed", True):
        raise ValueError("trap is not armed")
    trap["armed"] = False
    return extra


def trigger_trap(extra: dict | None, trap_id: str) -> tuple[dict, dict]:
    extra, trap = _mutate_trap(extra, trap_id)
    if not trap.get("armed", True):
        raise ValueError("trap is not armed")
    trap["armed"] = False
    trap["spotted"] = True
    sprung = {
        "id": str(trap.get("id")),
        "name": str(trap.get("name") or "Trap"),
        "damage": max(0, int(trap.get("damage") or 1)),
        "damage_type": trap.get("damage_type") or trap.get("type"),
    }
    return extra, sprung


def heard_rumors(world_state: dict | None) -> list[str]:
    out: list[str] = []
    for row in (world_state or {}).get("rumors") or []:
        if not isinstance(row, dict) or not row.get("heard"):
            continue
        text = str(row.get("text") or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def hear_rumor(world_state: dict | None, rumor_id: str | None = None, text: str | None = None) -> tuple[dict, str]:
    ws = dict(world_state or {})
    rumors = [dict(row) if isinstance(row, dict) else row for row in (ws.get("rumors") or [])]
    rid = str(rumor_id or "").strip().lower()
    needle = str(text or "").strip().lower()
    for row in rumors:
        if not isinstance(row, dict):
            continue
        if rid and str(row.get("id") or "").strip().lower() == rid:
            found = row
            break
        if needle and str(row.get("text") or "").strip().lower() == needle:
            found = row
            break
    else:
        raise ValueError("rumor not found")
    body = str(found.get("text") or "").strip()
    if not body:
        raise ValueError("rumor not found")
    found["heard"] = True
    ws["rumors"] = rumors
    return ws, body


def unheard_rumor_ids(world_state: dict | None) -> list[str]:
    out: list[str] = []
    for row in (world_state or {}).get("rumors") or []:
        if not isinstance(row, dict) or row.get("heard"):
            continue
        rid = str(row.get("id") or "").strip()
        if rid and rid not in out:
            out.append(rid)
    return out


def _shuffle(rng, items: list) -> list:
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = rng.randint(0, i)
        items[i], items[j] = items[j], items[i]
    return items


def seed_rumors(
    world_state: dict | None,
    *,
    place: str = "",
    people: list[str] | None = None,
    quests: list[str] | None = None,
    rng=None,
) -> dict:
    ws = dict(world_state or {})
    rumors = [row for row in (ws.get("rumors") or []) if isinstance(row, dict)]
    unheard = sum(1 for row in rumors if not row.get("heard"))
    if unheard >= 2:
        ws["rumors"] = rumors[:12]
        return ws
    place = (place or "town").strip() or "town"
    who = next((n for n in (people or []) if str(n).strip()), "a traveler")
    job = next((q for q in (quests or []) if str(q).strip()), "")
    templates = [
        ("loc-watch", f"The night watch in {place} has been taking bribes."),
        ("loc-well", f"The well at {place} soured after a stranger passed through."),
        ("npc-debt", f"{who} owes money to people who collect after dark."),
        (
            "quest-whisper",
            f"Someone is hiring quietly for '{job}'." if job else f"A job notice in {place} was torn down overnight.",
        ),
        ("loc-cellar", f"There is a locked cellar under {place} that locals will not discuss."),
    ]
    ids = {str(row.get("id") or "") for row in rumors}
    if rng is None:
        import random as _random

        rng = _random.Random()
    for rid, text in _shuffle(rng, templates):
        if rid in ids:
            continue
        rumors.append({"id": rid, "text": text, "heard": False})
        ids.add(rid)
        if sum(1 for row in rumors if not row.get("heard")) >= 2:
            break
    ws["rumors"] = rumors[:12]
    return ws


GRID = 8
FT_PER_CELL = 5


def clamp_cell(value: int) -> int:
    return max(0, min(GRID - 1, int(value)))


def cell_pos(extra: dict | None) -> tuple[int, int]:
    data = extra or {}
    return clamp_cell(data.get("x", 3)), clamp_cell(data.get("y", 3))


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def distance_ft(a_extra: dict | None, b_extra: dict | None) -> int:
    return chebyshev(cell_pos(a_extra), cell_pos(b_extra)) * FT_PER_CELL


def step_toward(frm: tuple[int, int], to: tuple[int, int]) -> tuple[int, int]:
    x, y = frm
    tx, ty = to
    if x < tx:
        x += 1
    elif x > tx:
        x -= 1
    if y < ty:
        y += 1
    elif y > ty:
        y -= 1
    return clamp_cell(x), clamp_cell(y)


def step_away(frm: tuple[int, int], threat: tuple[int, int]) -> tuple[int, int]:
    x, y = frm
    tx, ty = threat
    if x == tx and y == ty:
        return clamp_cell(x), clamp_cell(y + 1 if y < GRID - 1 else y - 1)
    if x < tx:
        x -= 1
    elif x > tx:
        x += 1
    if y < ty:
        y -= 1
    elif y > ty:
        y += 1
    return clamp_cell(x), clamp_cell(y)


def _slug(text: str) -> str:
    words = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text).split()
    return "-".join(words[:3]) or "topic"


def normalize_knowledge(knowledge, secrets=None) -> list[dict]:
    secret_set = {str(s).strip().lower() for s in (secrets or []) if str(s).strip()}
    out: list[dict] = []
    seen: set[str] = set()
    for item in knowledge or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            rid = str(item.get("id") or _slug(str(item.get("label") or text))).strip()
            label = str(item.get("label") or "").strip() or " ".join(text.split()[:4])
        else:
            text = str(item).strip()
            rid = _slug(text)
            label = " ".join(text.split()[:4])
        if not rid or not text:
            continue
        lowered = text.lower()
        if lowered in secret_set or any(s in lowered for s in secret_set if len(s) > 6):
            continue
        key = rid.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": rid, "label": label[:40], "text": text})
    return out[:8]


def public_topics(knowledge, secrets=None) -> list[dict]:
    return [{"id": row["id"], "label": row["label"]} for row in normalize_knowledge(knowledge, secrets)]


def packet_text(knowledge, topic_id: str, secrets=None) -> str:
    key = str(topic_id).strip().lower()
    for row in normalize_knowledge(knowledge, secrets):
        if row["id"].lower() == key:
            return row["text"]
    raise ValueError("topic unknown")


def heard_topics(extra: dict | None, npc_id) -> list[str]:
    raw = (extra or {}).get("heard_from") or {}
    if not isinstance(raw, dict):
        return []
    return [str(x) for x in (raw.get(str(npc_id)) or [])]


def mark_heard_topic(extra: dict | None, npc_id, topic_id: str) -> dict:
    data = dict(extra or {})
    heard = dict(data.get("heard_from") or {})
    key = str(npc_id)
    row = list(heard.get(key) or [])
    if topic_id not in row:
        row.append(str(topic_id))
    heard[key] = row[:20]
    data["heard_from"] = heard
    return data


def checkpoint_name(raw: str | None) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in (raw or "").strip())[:24].strip("-")
    return text or "camp"


def checkpoint_names(world_state: dict | None) -> list[str]:
    out: list[str] = []
    for row in (world_state or {}).get("checkpoints") or []:
        if not isinstance(row, dict):
            continue
        name = checkpoint_name(str(row.get("name") or ""))
        if name and name not in out:
            out.append(name)
    return out


def public_world_state(world_state: dict | None) -> dict:
    out = dict(world_state or {})
    out.pop("checkpoints", None)
    return out


def upsert_checkpoint(world_state: dict | None, name: str, payload: dict) -> dict:
    from app.game.rules import MAX_CHECKPOINTS

    ws = dict(world_state or {})
    key = checkpoint_name(name)
    rows = [dict(r) for r in (ws.get("checkpoints") or []) if isinstance(r, dict)]
    rows = [r for r in rows if checkpoint_name(str(r.get("name") or "")) != key]
    rows.append({"name": key, "payload": payload})
    ws["checkpoints"] = rows[-MAX_CHECKPOINTS:]
    return ws


def checkpoint_payload(world_state: dict | None, name: str) -> dict:
    key = checkpoint_name(name)
    for row in (world_state or {}).get("checkpoints") or []:
        if isinstance(row, dict) and checkpoint_name(str(row.get("name") or "")) == key:
            payload = row.get("payload")
            if isinstance(payload, dict):
                return payload
    raise ValueError("checkpoint not found")
