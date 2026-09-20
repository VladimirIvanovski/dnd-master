from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.database.models import Combatant, QuestObjective
from app.database.repositories import (
    CampaignRepository,
    CharacterRepository,
    CombatRepository,
    EventRepository,
    InventoryRepository,
    LocationRepository,
    NPCRepository,
    QuestRepository,
    RelationshipRepository,
)
from app.game.clock import advance_world_time, is_time_regression, period_label, time_ordinal
from app.game.dice import SecureRandom, ability_modifier, roll_dice, roll_d20, skill_check
from app.game.rules import (
    MAX_GOLD_GAIN,
    MAX_ITEM_QTY,
    RESTRICTED_ITEM_TYPES,
    EXHAUSTED_CHECK_PENALTY,
    base_ac,
    carry_capacity,
    clamp_vitals,
    conditions_from_extra,
    extra_with_conditions,
    is_consumable,
    item_slot,
    item_weight,
    tick_vitals,
    vitals_from_extra,
    weather_check_penalty,
    weather_travel_ticks,
)
from app.game.worldkit import (
    add_fact,
    add_to_stock,
    apply_resistance,
    cell_pos,
    checkpoint_payload,
    chebyshev,
    clamp_cell,
    cover_bonus,
    disarm_trap,
    distance_ft,
    faction_delta,
    first_armed_trap_id,
    hear_rumor,
    lighting_of,
    loot_container,
    mark_heard_topic,
    normalize_stock,
    packet_text,
    range_ft,
    record_death_save,
    reset_death_saves,
    scheduled_location,
    seed_rumors,
    spot_trap,
    step_away,
    step_toward,
    take_from_stock,
    trigger_trap,
    unlock_container,
    upsert_checkpoint,
)
from app.schemas.gameplay import DiceResultOut, StateChange
from app.utils.ids import utcnow

XP_THRESHOLDS = [0, 300, 900, 2700, 6500, 14000]

SKILL_TO_ABILITY = {
    "strength": "strength",
    "dexterity": "dexterity",
    "constitution": "constitution",
    "intelligence": "intelligence",
    "wisdom": "wisdom",
    "charisma": "charisma",
    "athletics": "strength",
    "acrobatics": "dexterity",
    "stealth": "dexterity",
    "perception": "wisdom",
    "insight": "wisdom",
    "persuasion": "charisma",
    "deception": "charisma",
    "investigation": "intelligence",
    "lockpick": "dexterity",
    "sleight of hand": "dexterity",
    "survival": "wisdom",
    "intimidation": "charisma",
    "performance": "charisma",
    "nature": "intelligence",
    "history": "intelligence",
    "arcana": "intelligence",
    "medicine": "wisdom",
    "animal handling": "wisdom",
}


@dataclass
class ApplyResult:
    applied: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    dice_results: list[DiceResultOut] = field(default_factory=list)
    event_summaries: list[str] = field(default_factory=list)


class GameEngine:
    """Deterministic mechanics authority. LLM proposals are validated here."""

    ALLOWED_ACTIONS = {
        "apply_damage",
        "heal",
        "add_item",
        "gain_item",
        "remove_item",
        "gain_xp",
        "gain_gold",
        "spend_gold",
        "subtract_gold",
        "gain_silver",
        "spend_silver",
        "gain_copper",
        "spend_copper",
        "move_to_location",
        "start_quest",
        "update_quest",
        "complete_quest",
        "change_relationship",
        "spawn_npc",
        "update_npc",
        "start_combat",
        "end_combat",
        "damage_combatant",
        "advance_turn",
        "set_world_flag",
        "set_time",
        "set_weather",
        "advance_time",
        "equip_item",
        "unequip_item",
        "consume_item",
        "use_item",
        "apply_condition",
        "remove_condition",
        "set_temp_hp",
        "rest",
        "buy_item",
        "sell_item",
        "flee_combat",
        "lock_location",
        "unlock_location",
        "learn_fact",
        "change_faction_rep",
        "set_lighting",
        "unlock_container",
        "loot_container",
        "death_save",
        "set_combatant_cover",
        "set_combatant_range",
        "move_combatant",
        "spot_trap",
        "disarm_trap",
        "trigger_trap",
        "hear_rumor",
        "share_knowledge",
        "save_checkpoint",
        "load_checkpoint",
    }

    def __init__(self, db: Session, rng: random.Random | SecureRandom | None = None):
        self.db = db
        self.rng = rng or SecureRandom()
        self.campaigns = CampaignRepository(db)
        self.characters = CharacterRepository(db)
        self.inventory = InventoryRepository(db)
        self.events = EventRepository(db)
        self.locations = LocationRepository(db)
        self.npcs = NPCRepository(db)
        self.quests = QuestRepository(db)
        self.relationships = RelationshipRepository(db)
        self.combat = CombatRepository(db)

    def roll_d20(self):
        return roll_d20(self.rng)

    def roll_dice(self, notation: str):
        return roll_dice(notation, self.rng)

    def skill_check(self, ability_score: int, dc: int, proficiency_bonus: int = 0):
        return skill_check(ability_score, dc, proficiency_bonus=proficiency_bonus, rng=self.rng)

    def attack_roll(self, attack_bonus: int, target_ac: int) -> tuple[object, bool, int]:
        roll = self.roll_d20()
        total = roll.total + attack_bonus
        return roll, total >= target_ac, total

    def calculate_damage(self, notation: str) -> int:
        return self.roll_dice(notation).total

    def apply_damage(
        self, character_id: uuid.UUID, amount: int, damage_type: str | None = None
    ) -> int:
        character = self.characters.get(character_id)
        if not character or amount < 0:
            raise ValueError("Invalid damage")
        if self._is_dead(character):
            raise ValueError("character is dead")
        remaining = apply_resistance(amount, character.extra, damage_type)
        was_down = character.hp <= 0
        temp = int(getattr(character, "temp_hp", 0) or 0)
        if temp > 0:
            absorbed = min(temp, remaining)
            character.temp_hp = temp - absorbed
            remaining -= absorbed
        character.hp = max(0, character.hp - remaining)
        if was_down and remaining > 0:
            extra, outcome = record_death_save(character.extra, success=False)
            character.extra = extra
            if outcome == "dead":
                self._set_condition(character, "dead")
            elif character.hp <= 0:
                self._set_condition(character, "unconscious")
        elif character.hp <= 0:
            self._set_condition(character, "unconscious")
        self.db.flush()
        return character.hp

    def heal(self, character_id: uuid.UUID, amount: int) -> int:
        character = self.characters.get(character_id)
        if not character or amount < 0:
            raise ValueError("Invalid heal")
        if self._is_dead(character):
            raise ValueError("character is dead")
        character.hp = min(character.max_hp, character.hp + amount)
        if character.hp > 0:
            self._clear_condition(character, "unconscious")
            self._clear_condition(character, "stable")
            character.extra = reset_death_saves(character.extra)
        self.db.flush()
        return character.hp

    def add_item(self, character_id: uuid.UUID, campaign_id: uuid.UUID, name: str, quantity: int = 1, **kwargs):
        self._ensure_carry_room(character_id, extra_weight=self._incoming_weight(kwargs, quantity))
        return self.inventory.add_item(character_id, campaign_id, name, quantity=quantity, **kwargs)

    def _assert_add_item_origin(
        self,
        campaign_id: uuid.UUID,
        character_id: uuid.UUID,
        name: str,
        item_type: str,
        props: dict,
        params: dict,
    ) -> None:
        unique = bool(props.get("unique") or params.get("unique"))
        kind = (item_type or "misc").lower()
        if not unique and kind not in RESTRICTED_ITEM_TYPES:
            return
        source = str(params.get("source") or "").strip().lower()
        if source not in {"gift", "loot", "reward"}:
            raise ValueError("cannot conjure that item")
        ch = self.characters.get(character_id)
        if source == "gift":
            loc_id = ch.location_id if ch else None
            if not loc_id or not any(n.is_alive for n in self.npcs.nearby(loc_id)):
                raise ValueError("nobody here to give that")
        elif source == "loot":
            if self.combat.active_for_campaign(campaign_id):
                return
            loc = self.locations.get(ch.location_id) if ch and ch.location_id else None
            boxes = (loc.extra or {}).get("containers") if loc else None
            if not boxes:
                raise ValueError("nothing here to loot")
        elif source == "reward":
            if not self.quests.active_for_campaign(campaign_id, character_id):
                raise ValueError("no quest reward due")

    def remove_item(self, character_id: uuid.UUID, item_id: uuid.UUID, quantity: int = 1) -> bool:
        return self.inventory.remove_item(character_id, item_id, quantity)

    def gain_xp(self, character_id: uuid.UUID, amount: int) -> tuple[int, int]:
        character = self.characters.get(character_id)
        if not character or amount < 0:
            raise ValueError("Invalid XP")
        character.xp += amount
        while (
            character.level < len(XP_THRESHOLDS)
            and character.xp >= XP_THRESHOLDS[character.level]
        ):
            character.level += 1
            character.max_hp += 5
            character.hp = character.max_hp
        self.db.flush()
        return character.xp, character.level

    def _incoming_weight(self, kwargs: dict, quantity: int) -> int:
        from app.game.rules import DEFAULT_WEIGHT

        weight = int(kwargs.get("weight") or 0)
        if weight > 0:
            return weight * quantity
        kind = str(kwargs.get("item_type") or "misc").lower()
        return DEFAULT_WEIGHT.get(kind, 1) * quantity

    def _carry_used(self, character_id: uuid.UUID) -> int:
        return sum(item_weight(row.item) * row.quantity for row in self.inventory.list_for_character(character_id))

    def _ensure_carry_room(self, character_id: uuid.UUID, extra_weight: int = 0) -> None:
        ch = self.characters.get(character_id)
        if not ch:
            raise ValueError("Invalid character")
        cap = carry_capacity(ch.strength)
        if self._carry_used(character_id) + extra_weight > cap:
            raise ValueError("too heavy to carry")

    def _set_condition(self, character, name: str) -> None:
        names = conditions_from_extra(character.extra)
        if name not in names:
            names.append(name)
        character.extra = extra_with_conditions(character.extra, names)

    def _clear_condition(self, character, name: str) -> None:
        names = [n for n in conditions_from_extra(character.extra) if n != name]
        character.extra = extra_with_conditions(character.extra, names)

    def _recalc_ac(self, character_id: uuid.UUID) -> None:
        ch = self.characters.get(character_id)
        if not ch:
            return
        bonus = 0
        for row in self.inventory.list_for_character(character_id):
            if not row.equipped:
                continue
            props = row.item.properties or {}
            bonus += int(props.get("ac_bonus") or 0)
        ch.ac = base_ac(ch.dexterity) + bonus
        self.db.flush()

    def _equip(self, character_id: uuid.UUID, item_id: uuid.UUID) -> str:
        link = self.inventory.get_link(character_id, item_id)
        if not link:
            raise ValueError("item not in inventory")
        slot = item_slot(link.item.item_type, link.item.properties)
        if not slot:
            raise ValueError("item cannot be equipped")
        if link.durability is not None and link.durability <= 0:
            raise ValueError("item is broken")
        for other in self.inventory.list_for_character(character_id):
            if other.id == link.id or not other.equipped:
                continue
            if item_slot(other.item.item_type, other.item.properties) == slot:
                other.equipped = False
        link.equipped = True
        self.db.flush()
        self._recalc_ac(character_id)
        return f"equipped {link.item.name}"

    def _unequip(self, character_id: uuid.UUID, item_id: uuid.UUID) -> str:
        link = self.inventory.get_link(character_id, item_id)
        if not link:
            raise ValueError("item not in inventory")
        link.equipped = False
        self.db.flush()
        self._recalc_ac(character_id)
        return f"unequipped {link.item.name}"

    def _consume(self, character_id: uuid.UUID, item_id: uuid.UUID) -> str:
        link = self.inventory.get_link(character_id, item_id)
        if not link:
            raise ValueError("item not in inventory")
        if not is_consumable(link.item):
            raise ValueError("item is not consumable")
        props = link.item.properties or {}
        heal_amt = int(props.get("heal") or 0)
        food = int(props.get("hunger") or (40 if (link.item.item_type or "").lower() == "food" else 0))
        drink = int(props.get("thirst") or (40 if (link.item.item_type or "").lower() == "drink" else 0))
        if not self.inventory.remove_item(character_id, item_id, 1):
            raise ValueError("item not in inventory")
        ch = self.characters.get(character_id)
        if heal_amt:
            self.heal(character_id, heal_amt)
        vitals = clamp_vitals(
            **{
                **vitals_from_extra(ch.extra),
                "hunger": vitals_from_extra(ch.extra)["hunger"] - food,
                "thirst": vitals_from_extra(ch.extra)["thirst"] - drink,
            }
        )
        extra = dict(ch.extra or {})
        extra.update(vitals)
        ch.extra = extra
        self.db.flush()
        return f"consumed {link.item.name}"

    def _is_dead(self, character) -> bool:
        return "dead" in conditions_from_extra(character.extra)

    def _has_ranged_weapon(self, character_id: uuid.UUID) -> bool:
        ranged_types = {"bow", "ranged", "crossbow", "thrown"}
        for row in self.inventory.list_for_character(character_id):
            if not row.equipped:
                continue
            props = row.item.properties or {}
            kind = (row.item.item_type or "").lower()
            if props.get("ranged") or kind in ranged_types:
                return True
        return False

    def _tick_schedules(self, campaign_id: uuid.UUID) -> None:
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return
        label = period_label(campaign.current_time)
        if not label:
            return
        for npc in self.npcs.list_for_campaign(campaign_id):
            if not npc.is_alive:
                continue
            dest = scheduled_location(npc.extra, label)
            if not dest:
                continue
            try:
                loc_id = uuid.UUID(str(dest))
            except ValueError:
                continue
            loc = self.locations.get(loc_id)
            if loc and loc.campaign_id == campaign_id:
                npc.location_id = loc_id
        self.db.flush()

    def _npc_extra_from_params(self, p: dict) -> dict:
        extra = dict(p.get("extra") or {})
        if "stock" in p:
            extra["stock"] = normalize_stock(p.get("stock"))
        if "schedule" in p and isinstance(p.get("schedule"), dict):
            extra["schedule"] = dict(p["schedule"])
        if "gold" in p:
            extra["gold"] = max(0, int(p["gold"]))
        return extra

    def _container_location(self, campaign_id: uuid.UUID, character_id: uuid.UUID, p: dict):
        loc_id = p.get("location_id")
        loc = self.locations.get(uuid.UUID(str(loc_id))) if loc_id else None
        if loc is None:
            ch = self.characters.get(character_id)
            loc = self.locations.get(ch.location_id) if ch and ch.location_id else None
        if not loc or loc.campaign_id != campaign_id:
            raise ValueError("invalid location")
        return loc

    def _active_combatant(self, campaign_id: uuid.UUID, combatant_id: uuid.UUID):
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            raise ValueError("no active combat")
        target = next((c for c in session.combatants if c.id == combatant_id), None)
        if not target:
            raise ValueError("combatant not found")
        return target

    def _rest(self, character_id: uuid.UUID, campaign_id: uuid.UUID) -> str:
        if self.combat.active_for_campaign(campaign_id):
            raise ValueError("cannot rest during combat")
        ch = self.characters.get(character_id)
        if self._is_dead(ch):
            raise ValueError("character is dead")
        extra = dict(ch.extra or {})
        vitals = vitals_from_extra(extra)
        vitals["stamina"] = 100
        vitals["hunger"] = min(100, vitals["hunger"] + 8)
        vitals["thirst"] = min(100, vitals["thirst"] + 12)
        extra.update(clamp_vitals(**vitals))
        names = [n for n in conditions_from_extra(extra) if n not in {"exhausted"}]
        extra = extra_with_conditions(extra, names)
        ch.extra = extra
        self.heal(character_id, max(1, ch.level))
        campaign = self.campaigns.get(campaign_id)
        campaign.current_time = advance_world_time(campaign.current_time, 1)
        self.db.flush()
        self._tick_schedules(campaign_id)
        self._seed_world_rumors(campaign_id, character_id)
        return "rested"

    def _tick_character_vitals(self, character_id: uuid.UUID, steps: int = 1) -> None:
        ch = self.characters.get(character_id)
        if not ch:
            return
        ch.extra = tick_vitals(ch.extra, steps)
        self.db.flush()

    def assert_invariants(self, character_id: uuid.UUID) -> None:
        ch = self.characters.get(character_id)
        if not ch:
            raise ValueError("Invalid character")
        if ch.gold < 0 or ch.silver < 0 or ch.copper < 0:
            raise ValueError("negative currency")
        if ch.xp < 0 or ch.level < 1:
            raise ValueError("invalid progression")
        if ch.hp < 0 or ch.hp > ch.max_hp:
            raise ValueError("invalid hp")
        if int(getattr(ch, "temp_hp", 0) or 0) < 0:
            raise ValueError("invalid temp hp")
        seen_slots: set[str] = set()
        for row in self.inventory.list_for_character(character_id):
            if row.quantity < 1:
                raise ValueError("negative inventory")
            if row.equipped:
                slot = item_slot(row.item.item_type, row.item.properties)
                if slot:
                    if slot in seen_slots:
                        raise ValueError("duplicate equipped slot")
                    seen_slots.add(slot)
        if self._carry_used(character_id) > carry_capacity(ch.strength):
            raise ValueError("overencumbered")

    def _wear_equipped_weapons(self, character_id: uuid.UUID) -> None:
        dirty = False
        for row in self.inventory.list_for_character(character_id):
            if not row.equipped or item_slot(row.item.item_type, row.item.properties) != "weapon":
                continue
            if row.durability is None:
                continue
            row.durability = max(0, int(row.durability) - 1)
            dirty = True
            if row.durability <= 0:
                row.equipped = False
        if dirty:
            self.db.flush()
            self._recalc_ac(character_id)

    def _capture_checkpoint(self, campaign_id: uuid.UUID, character_id: uuid.UUID) -> dict:
        ch = self.characters.get(character_id)
        campaign = self.campaigns.get(campaign_id)
        if not ch or not campaign:
            raise ValueError("invalid character")
        pack = []
        for row in self.inventory.list_for_character(character_id):
            pack.append(
                {
                    "name": row.item.name,
                    "quantity": row.quantity,
                    "item_type": row.item.item_type,
                    "description": row.item.description or "",
                    "weight": row.item.weight,
                    "value_gold": row.item.value_gold,
                    "properties": dict(row.item.properties or {}),
                    "equipped": bool(row.equipped),
                    "durability": row.durability,
                }
            )
        return {
            "hp": ch.hp,
            "max_hp": ch.max_hp,
            "temp_hp": int(getattr(ch, "temp_hp", 0) or 0),
            "xp": ch.xp,
            "level": ch.level,
            "gold": ch.gold,
            "silver": ch.silver,
            "copper": ch.copper,
            "location_id": str(ch.location_id) if ch.location_id else None,
            "extra": dict(ch.extra or {}),
            "current_time": campaign.current_time,
            "weather": campaign.weather,
            "inventory": pack,
        }

    def _restore_checkpoint(self, campaign_id: uuid.UUID, character_id: uuid.UUID, payload: dict) -> None:
        from sqlalchemy.orm.attributes import flag_modified

        ch = self.characters.get(character_id)
        campaign = self.campaigns.get(campaign_id)
        if not ch or not campaign:
            raise ValueError("invalid character")
        loc_id = payload.get("location_id")
        if loc_id:
            loc = self.locations.get(uuid.UUID(str(loc_id)))
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            ch.location_id = loc.id
        ch.hp = int(payload.get("hp", ch.hp))
        ch.max_hp = int(payload.get("max_hp", ch.max_hp))
        ch.temp_hp = int(payload.get("temp_hp", 0) or 0)
        ch.xp = int(payload.get("xp", ch.xp))
        ch.level = int(payload.get("level", ch.level))
        ch.gold = int(payload.get("gold", 0) or 0)
        ch.silver = int(payload.get("silver", 0) or 0)
        ch.copper = int(payload.get("copper", 0) or 0)
        ch.extra = dict(payload.get("extra") or {})
        flag_modified(ch, "extra")
        campaign.current_time = str(payload.get("current_time") or campaign.current_time)
        campaign.weather = str(payload.get("weather") or campaign.weather)
        for row in list(self.inventory.list_for_character(character_id)):
            self.inventory.remove_item(character_id, row.item_id, row.quantity)
        for item in payload.get("inventory") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            qty = max(1, int(item.get("quantity") or 1))
            props = dict(item.get("properties") or {})
            link = self.add_item(
                character_id,
                campaign_id,
                name,
                quantity=qty,
                item_type=str(item.get("item_type") or "misc"),
                description=str(item.get("description") or ""),
                weight=int(item.get("weight") or 0),
                value_gold=int(item.get("value_gold") or 0),
                properties=props,
            )
            if item.get("durability") is not None:
                link.durability = int(item["durability"])
            if item.get("equipped"):
                try:
                    self._equip(character_id, link.item_id)
                except ValueError:
                    pass
        self.db.flush()
        self._recalc_ac(character_id)


    def change_relationship(
        self,
        character_id: uuid.UUID,
        npc_id: uuid.UUID,
        *,
        trust_delta: float = 0,
        fear_delta: float = 0,
        respect_delta: float = 0,
    ):
        rel = self.relationships.get_or_create(character_id, npc_id)

        def clamp(v: float) -> float:
            return max(-100.0, min(100.0, v))

        rel.trust = clamp(rel.trust + trust_delta)
        rel.fear = clamp(rel.fear + fear_delta)
        rel.respect = clamp(rel.respect + respect_delta)
        self.db.flush()
        return rel

    def start_combat(self, campaign_id: uuid.UUID, combatants: list[dict]) -> object:
        existing = self.combat.active_for_campaign(campaign_id)
        if existing:
            raise ValueError("Combat already active")
        session = self.combat.create(campaign_id=campaign_id, status="active")
        built = []
        player_cells = [(3, 1), (2, 1), (4, 1)]
        enemy_cells = [(3, 6), (2, 6), (4, 6), (1, 6), (5, 6)]
        pi = 0
        ei = 0
        for c in combatants:
            raw_ref = c.get("ref_id")
            ref_id = uuid.UUID(str(raw_ref)) if raw_ref else None
            kind = str(c.get("combatant_type") or "enemy")
            ai = str(c.get("ai") or ("ranged" if c.get("ranged") else "melee")).lower()
            if "x" in c or "y" in c:
                x, y = clamp_cell(c.get("x", 3)), clamp_cell(c.get("y", 3))
            elif kind in {"player", "character"}:
                x, y = player_cells[pi % len(player_cells)]
                pi += 1
            else:
                x, y = enemy_cells[ei % len(enemy_cells)]
                ei += 1
            built.append(
                Combatant(
                    session_id=session.id,
                    name=c["name"],
                    combatant_type=kind,
                    ref_id=ref_id,
                    initiative=int(c.get("initiative", self.roll_d20().total)),
                    hp=c.get("hp", 10),
                    max_hp=c.get("max_hp", c.get("hp", 10)),
                    ac=c.get("ac", 10),
                    extra={
                        "cover": int(c.get("cover") or 0),
                        "x": x,
                        "y": y,
                        "ai": ai,
                        "ranged": bool(c.get("ranged") or ai == "ranged"),
                    },
                )
            )
        built.sort(key=lambda x: x.initiative, reverse=True)
        for c in built:
            self.db.add(c)
        session.extra = {
            **(session.extra or {}),
            "turn_index": 0,
            "turn_moved": False,
            "turn_struck": False,
        }
        self.db.flush()
        self._refresh_ranges(built)
        return session

    def _is_player_combatant(self, combatant) -> bool:
        return bool(combatant) and combatant.combatant_type in {"player", "character"}

    def _pass_turn(self, session) -> None:
        active = [c for c in session.combatants if c.is_active]
        active.sort(key=lambda c: c.initiative, reverse=True)
        if not active:
            return
        idx = int((session.extra or {}).get("turn_index", 0))
        idx = (idx + 1) % len(active)
        if idx == 0:
            session.round_number += 1
        session.extra = {
            **(session.extra or {}),
            "turn_index": idx,
            "turn_moved": False,
            "turn_struck": False,
        }
        self.db.flush()

    def _consume_act(self, session, key: str) -> None:
        extra = dict(session.extra or {})
        if extra.get(key):
            raise ValueError("already moved" if key == "turn_moved" else "already attacked")
        extra[key] = True
        session.extra = extra

    def _require_own_turn(self, session, combatant) -> None:
        current = self._current_fighter(session)
        if not current or current.id != combatant.id:
            raise ValueError("not their turn")

    def _require_player_turn(self, session) -> None:
        current = self._current_fighter(session)
        if not current or not self._is_player_combatant(current):
            raise ValueError("not your turn")

    def _refresh_ranges(self, combatants) -> None:
        player = next(
            (c for c in combatants if c.combatant_type in {"player", "character"} and c.is_active),
            None,
        )
        if not player:
            return
        for c in combatants:
            extra = dict(c.extra or {})
            extra["range_ft"] = 0 if c.id == player.id else distance_ft(extra, player.extra)
            c.extra = extra

    def _seed_world_rumors(self, campaign_id: uuid.UUID, character_id: uuid.UUID) -> None:
        campaign = self.campaigns.get(campaign_id)
        ch = self.characters.get(character_id)
        if not campaign or not ch:
            return
        loc = self.locations.get(ch.location_id) if ch.location_id else None
        people = [n.name for n in self.npcs.nearby(loc.id)] if loc else []
        quests = [q.title for q in self.quests.active_for_campaign(campaign_id, character_id)]
        campaign.world_state = seed_rumors(
            campaign.world_state,
            place=loc.name if loc else campaign.name,
            people=people,
            quests=quests,
            rng=self.rng,
        )
        self.db.flush()

    def _current_fighter(self, session):
        active = [c for c in session.combatants if c.is_active]
        active.sort(key=lambda c: c.initiative, reverse=True)
        if not active:
            return None
        idx = int((session.extra or {}).get("turn_index", 0)) % len(active)
        return active[idx]

    def _enemy_act(self, campaign_id: uuid.UUID, character_id: uuid.UUID, attacker) -> str:
        if attacker.combatant_type not in {"enemy", "npc"}:
            return ""
        ch = self.characters.get(character_id)
        if not ch or self._is_dead(ch) or ch.hp <= 0:
            return ""
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            return ""
        player = next(
            (
                c
                for c in session.combatants
                if c.combatant_type in {"player", "character"} and c.is_active
            ),
            None,
        )
        if player:
            here = cell_pos(attacker.extra)
            goal = cell_pos(player.extra)
            dist = chebyshev(here, goal)
            extra = dict(attacker.extra or {})
            ai = str(extra.get("ai") or "melee").lower()
            ranged = bool(extra.get("ranged") or ai == "ranged")
            wounded = attacker.max_hp > 0 and attacker.hp * 3 <= attacker.max_hp
            if (ai == "skittish" or wounded) and dist <= 1 and attacker.hp < attacker.max_hp:
                nx, ny = step_away(here, goal)
                extra["x"], extra["y"] = nx, ny
                extra["cover"] = max(cover_bonus(extra), 2)
                attacker.extra = extra
                self._refresh_ranges(session.combatants)
                self.db.flush()
                return f"{attacker.name} falls back"
            if dist > 1 and ranged:
                amount = self.rng.randint(1, 2)
                hp = self.apply_damage(character_id, amount)
                player.hp = hp
                if hp <= 0:
                    player.is_active = False
                self.db.flush()
                return f"{attacker.name} shoots ({amount})"
            if dist > 1:
                nx, ny = step_toward(here, goal)
                extra["x"], extra["y"] = nx, ny
                attacker.extra = extra
                self._refresh_ranges(session.combatants)
                if chebyshev((nx, ny), goal) > 1:
                    self.db.flush()
                    return f"{attacker.name} closes in"
        amount = self.rng.randint(1, 3)
        hp = self.apply_damage(character_id, amount)
        if player:
            player.hp = hp
            if hp <= 0:
                player.is_active = False
        self.db.flush()
        return f"{attacker.name} strikes ({amount})"

    def end_combat(
        self,
        campaign_id: uuid.UUID,
        *,
        character_id: uuid.UUID | None = None,
        reward_xp: int = 0,
        reward_gold: int = 0,
    ) -> bool:
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            return False
        session.status = "ended"
        session.ended_at = utcnow()
        if character_id:
            if reward_xp > 0:
                self.gain_xp(character_id, min(reward_xp, 500))
            if reward_gold > 0:
                ch = self.characters.get(character_id)
                ch.gold += min(reward_gold, MAX_GOLD_GAIN)
        self.db.flush()
        return True

    def damage_combatant(
        self,
        campaign_id: uuid.UUID,
        combatant_id: uuid.UUID,
        amount: int,
        *,
        character_id: uuid.UUID | None = None,
    ) -> str:
        if amount < 0:
            raise ValueError("Invalid damage")
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            raise ValueError("no active combat")
        if character_id:
            self._require_player_turn(session)
        target = next((c for c in session.combatants if c.id == combatant_id), None)
        if not target or not target.is_active:
            raise ValueError("combatant not found")
        if range_ft(target.extra) > 5 and character_id and not self._has_ranged_weapon(character_id):
            raise ValueError("target out of melee range")
        if character_id:
            self._consume_act(session, "turn_struck")
        target.hp = max(0, target.hp - amount)
        if target.hp <= 0:
            target.is_active = False
            # Keep persistent NPC roster in sync so corpses leave "nearby".
            npc = None
            if target.ref_id:
                npc = self.npcs.get(target.ref_id)
            if npc is None and target.name:
                from sqlalchemy import select
                from app.database.models import NPC

                npc = self.db.scalar(
                    select(NPC).where(
                        NPC.campaign_id == campaign_id,
                        NPC.name == target.name,
                        NPC.is_alive.is_(True),
                    )
                )
            if npc and npc.campaign_id == campaign_id:
                npc.is_alive = False
                npc.hp = 0
            self.db.flush()
            return f"{target.name} defeated"
        self.db.flush()
        return f"{target.name} hp={target.hp}"

    def advance_turn(self, campaign_id: uuid.UUID, character_id: uuid.UUID | None = None) -> str:
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            raise ValueError("no active combat")
        active = [c for c in session.combatants if c.is_active]
        if not active:
            self.end_combat(campaign_id)
            return "combat ended — no active combatants"
        self._pass_turn(session)
        current = self._current_fighter(session)
        note = ""
        if character_id and current:
            note = self._enemy_act(campaign_id, character_id, current)
        suffix = f"; {note}" if note else ""
        who = current.name if current else "none"
        return f"round {session.round_number} turn: {who}{suffix}"

    def apply_state_changes(
        self,
        *,
        campaign_id: uuid.UUID,
        character_id: uuid.UUID,
        changes: list[StateChange],
    ) -> ApplyResult:
        result = ApplyResult()
        for change in changes:
            nested = self.db.begin_nested()
            try:
                msg = self._apply_one(campaign_id, character_id, change)
                nested.commit()
                result.applied.append(msg)
            except Exception as exc:  # noqa: BLE001 — validate proposals
                nested.rollback()
                result.rejected.append(f"{change.action}: {exc}")
        try:
            self.assert_invariants(character_id)
        except Exception as exc:  # noqa: BLE001
            result.rejected.append(f"invariants: {exc}")
        return result

    def _apply_one(
        self, campaign_id: uuid.UUID, character_id: uuid.UUID, change: StateChange
    ) -> str:
        action = change.action
        p = change.params
        if action == "gain_item":
            action = "add_item"
        if action == "subtract_gold":
            action = "spend_gold"
        if action in {"move_to", "move", "travel_to"}:
            action = "move_to_location"
        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Unknown action {action}")

        if action == "apply_damage":
            hp = self.apply_damage(
                character_id,
                int(p.get("amount", 0)),
                damage_type=p.get("damage_type") or p.get("type"),
            )
            return f"damage -> hp={hp}"
        if action == "heal":
            hp = self.heal(character_id, int(p.get("amount", 0)))
            return f"heal -> hp={hp}"
        if action == "add_item":
            qty = int(p.get("quantity", 1))
            if qty < 1 or qty > MAX_ITEM_QTY:
                raise ValueError("invalid quantity")
            name = (
                p.get("name")
                or p.get("item_name")
                or p.get("item")
                or p.get("title")
            )
            if not name or not str(name).strip():
                raise ValueError("item name required")
            name = str(name).strip()
            props = dict(p.get("properties") or {})
            if p.get("unique"):
                props["unique"] = True
            if p.get("heal") is not None:
                props["heal"] = int(p["heal"])
            if p.get("consumable"):
                props["consumable"] = True
            item_type = str(p.get("item_type", "misc"))
            self._assert_add_item_origin(
                campaign_id, character_id, name, item_type, props, p
            )
            self.add_item(
                character_id,
                campaign_id,
                name,
                quantity=qty,
                item_type=item_type,
                description=str(p.get("description", "")),
                weight=int(p.get("weight") or 0),
                properties=props,
            )
            return f"added item {name}"
        if action == "buy_item":
            name = str(p.get("name") or p.get("item_name") or "").strip()
            if not name:
                raise ValueError("item name required")
            qty = int(p.get("quantity", 1))
            if qty < 1 or qty > MAX_ITEM_QTY:
                raise ValueError("invalid quantity")
            ch = self.characters.get(character_id)
            item_type = str(p.get("item_type", "misc"))
            price = int(p.get("price") or p.get("value_gold") or 0)
            npc_id = p.get("npc_id")
            if npc_id:
                npc = self.npcs.get(uuid.UUID(str(npc_id)))
                if not npc or npc.campaign_id != campaign_id or not npc.is_alive:
                    raise ValueError("merchant not here")
                if npc.location_id != ch.location_id:
                    raise ValueError("merchant not here")
                extra, row = take_from_stock(npc.extra, name, qty)
                price = row["price"] * qty
                item_type = row["item_type"]
                if ch.gold < price:
                    raise ValueError("not enough gold")
                ch.gold -= price
                npc.extra = extra
            else:
                if price < 0 or price > MAX_GOLD_GAIN:
                    raise ValueError("invalid price")
                if ch.gold < price:
                    raise ValueError("not enough gold")
                ch.gold -= price
            self.add_item(
                character_id,
                campaign_id,
                name,
                quantity=qty,
                item_type=item_type,
                description=str(p.get("description", "")),
                value_gold=price,
                weight=int(p.get("weight") or 0),
                properties=dict(p.get("properties") or {}),
            )
            self.db.flush()
            return f"bought {name} for {price} gp"
        if action == "sell_item":
            item_id = uuid.UUID(str(p["item_id"]))
            link = self.inventory.get_link(character_id, item_id)
            if not link:
                raise ValueError("item not in inventory")
            qty = int(p.get("quantity", 1))
            price = int(p.get("price") or link.item.value_gold or 0)
            if price < 0:
                raise ValueError("invalid price")
            npc = None
            npc_id = p.get("npc_id")
            if npc_id:
                npc = self.npcs.get(uuid.UUID(str(npc_id)))
                ch = self.characters.get(character_id)
                if not npc or npc.campaign_id != campaign_id or not npc.is_alive:
                    raise ValueError("merchant not here")
                if npc.location_id != ch.location_id:
                    raise ValueError("merchant not here")
                merchant_gold = int((npc.extra or {}).get("gold") or 0)
                if merchant_gold < price * qty:
                    raise ValueError("merchant cannot afford that")
            if link.equipped:
                link.equipped = False
            if not self.inventory.remove_item(character_id, item_id, qty):
                raise ValueError("item not found")
            if npc is not None:
                npc.extra = add_to_stock(
                    npc.extra, link.item.name, qty, price, link.item.item_type or "misc"
                )
            ch = self.characters.get(character_id)
            ch.gold += min(price * qty, MAX_GOLD_GAIN)
            self._recalc_ac(character_id)
            self.db.flush()
            return f"sold for {price} gp"
        if action == "remove_item":
            ok = self.remove_item(character_id, uuid.UUID(str(p["item_id"])), int(p.get("quantity", 1)))
            if not ok:
                raise ValueError("item not found")
            self._recalc_ac(character_id)
            return f"removed item {p['item_id']}"
        if action == "equip_item":
            return self._equip(character_id, uuid.UUID(str(p["item_id"])))
        if action == "unequip_item":
            return self._unequip(character_id, uuid.UUID(str(p["item_id"])))
        if action in {"consume_item", "use_item"}:
            return self._consume(character_id, uuid.UUID(str(p["item_id"])))
        if action == "apply_condition":
            ch = self.characters.get(character_id)
            name = str(p.get("name") or p.get("condition") or "").strip().lower()
            if not name:
                raise ValueError("condition required")
            self._set_condition(ch, name)
            self.db.flush()
            return f"condition {name}"
        if action == "remove_condition":
            ch = self.characters.get(character_id)
            name = str(p.get("name") or p.get("condition") or "").strip().lower()
            if not name:
                raise ValueError("condition required")
            self._clear_condition(ch, name)
            self.db.flush()
            return f"cleared {name}"
        if action == "set_temp_hp":
            ch = self.characters.get(character_id)
            amount = int(p.get("amount", 0))
            if amount < 0 or amount > 50:
                raise ValueError("invalid temp hp")
            ch.temp_hp = amount
            self.db.flush()
            return f"temp_hp={ch.temp_hp}"
        if action == "rest":
            return self._rest(character_id, campaign_id)
        if action == "spawn_npc":
            name = str(p.get("name") or "").strip()
            if not name:
                raise ValueError("npc name required")
            loc_id = p.get("location_id")
            location_id = uuid.UUID(str(loc_id)) if loc_id else None
            if location_id is None:
                ch = self.characters.get(character_id)
                location_id = ch.location_id if ch else None
            if location_id is None:
                raise ValueError("npc location required")
            existing = self.npcs.find_at_location(campaign_id, location_id, name)
            if existing:
                if p.get("title"):
                    existing.title = str(p["title"])
                if p.get("personality"):
                    existing.personality = str(p["personality"])
                self.db.flush()
                return f"npc present {existing.name}"
            title = str(p.get("title") or "").strip()
            personality = str(p.get("personality") or "").strip()
            goals = str(p.get("goals") or "").strip()
            knowledge = list(p.get("knowledge") or [])
            if not title or not personality:
                from app.utils.npc_variety import random_npc_seed

                flavor = random_npc_seed(avoid_names={name})
                title = title or flavor.title
                personality = personality or flavor.personality
                goals = goals or flavor.goals
                if not knowledge:
                    knowledge = list(flavor.knowledge or [])
            npc = self.npcs.create(
                campaign_id,
                name=name,
                location_id=location_id,
                title=title,
                personality=personality,
                goals=goals,
                secrets=list(p.get("secrets") or []),
                knowledge=knowledge,
                faction=str(p.get("faction") or ""),
                extra=self._npc_extra_from_params(p),
            )
            self._seed_world_rumors(campaign_id, character_id)
            return f"npc spawned {npc.name}"
        if action == "update_npc":
            npc = self.npcs.get(uuid.UUID(str(p["npc_id"])))
            if not npc or npc.campaign_id != campaign_id:
                raise ValueError("invalid npc")
            for key in ("title", "personality", "goals", "fears", "motivations", "faction"):
                if key in p:
                    setattr(npc, key, str(p[key]))
            if "hp" in p:
                npc.hp = max(0, int(p["hp"]))
            if "is_alive" in p:
                npc.is_alive = bool(p["is_alive"])
            elif npc.hp <= 0:
                npc.is_alive = False
            if not npc.is_alive:
                npc.hp = 0
            if "location_id" in p and p["location_id"]:
                if not npc.is_alive:
                    raise ValueError("dead npc cannot move")
                npc.location_id = uuid.UUID(str(p["location_id"]))
            extra = dict(npc.extra or {})
            changed = False
            if "stock" in p:
                extra["stock"] = normalize_stock(p.get("stock"))
                changed = True
            if "schedule" in p and isinstance(p.get("schedule"), dict):
                extra["schedule"] = dict(p["schedule"])
                changed = True
            if "gold" in p:
                extra["gold"] = max(0, int(p["gold"]))
                changed = True
            if changed:
                npc.extra = extra
            self.db.flush()
            return f"npc updated {npc.name}"
        if action == "gain_xp":
            amount = int(p.get("amount", 0))
            if amount < 0 or amount > 500:
                raise ValueError("invalid XP amount")
            xp, level = self.gain_xp(character_id, amount)
            return f"xp={xp} level={level}"
        if action == "gain_gold":
            amount = int(p.get("amount", p.get("gold", 0)))
            if amount <= 0:
                raise ValueError("gold gain must be positive")
            if amount > MAX_GOLD_GAIN:
                raise ValueError(f"gold gain exceeds max {MAX_GOLD_GAIN}")
            ch = self.characters.get(character_id)
            ch.gold += amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action in ("spend_gold", "subtract_gold"):
            ch = self.characters.get(character_id)
            amount = int(p.get("amount", p.get("gold", 0)))
            if amount <= 0:
                raise ValueError("gold spend must be positive")
            if ch.gold < amount:
                raise ValueError("not enough gold")
            ch.gold -= amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action == "gain_silver":
            amount = int(p.get("amount", p.get("silver", 0)))
            if amount <= 0 or amount > MAX_GOLD_GAIN * 10:
                raise ValueError("invalid silver amount")
            ch = self.characters.get(character_id)
            ch.silver += amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action == "spend_silver":
            ch = self.characters.get(character_id)
            amount = int(p.get("amount", p.get("silver", 0)))
            if amount <= 0:
                raise ValueError("silver spend must be positive")
            if ch.silver < amount:
                raise ValueError("not enough silver")
            ch.silver -= amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action == "gain_copper":
            amount = int(p.get("amount", p.get("copper", 0)))
            if amount <= 0 or amount > MAX_GOLD_GAIN * 100:
                raise ValueError("invalid copper amount")
            ch = self.characters.get(character_id)
            ch.copper += amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action == "spend_copper":
            ch = self.characters.get(character_id)
            amount = int(p.get("amount", p.get("copper", 0)))
            if amount <= 0:
                raise ValueError("copper spend must be positive")
            if ch.copper < amount:
                raise ValueError("not enough copper")
            ch.copper -= amount
            self.db.flush()
            return f"gp={ch.gold} sp={ch.silver} cp={ch.copper}"
        if action == "move_to_location":
            loc = None
            raw_id = p.get("location_id") or p.get("id")
            if raw_id:
                try:
                    loc = self.locations.get(uuid.UUID(str(raw_id)))
                except ValueError as exc:
                    raise ValueError("invalid location_id") from exc
            if loc is None:
                name = (
                    p.get("location_name")
                    or p.get("name")
                    or p.get("location")
                    or p.get("destination")
                )
                if name:
                    from app.visual.hashing import normalize_name

                    loc = self.locations.find_by_normalized(
                        campaign_id, normalize_name(str(name))
                    )
                    if loc is None:
                        # Soft match: any campaign location containing the name
                        from sqlalchemy import select
                        from app.database.models import Location

                        needle = str(name).strip().lower()
                        candidates = list(
                            self.db.scalars(
                                select(Location).where(Location.campaign_id == campaign_id)
                            ).all()
                        )
                        loc = next(
                            (c for c in candidates if needle in c.name.lower() or c.name.lower() in needle),
                            None,
                        )
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            loc_extra = loc.extra or {}
            if loc_extra.get("locked") and not loc_extra.get("unlocked"):
                raise ValueError("location is locked")
            ch = self.characters.get(character_id)
            ch.location_id = loc.id
            loc.discovered = True
            trap_note = ""
            tid = first_armed_trap_id(loc.extra)
            if tid:
                extra, sprung = trigger_trap(loc.extra, tid)
                loc.extra = extra
                self.apply_damage(
                    character_id,
                    sprung["damage"],
                    damage_type=sprung.get("damage_type"),
                )
                trap_note = f"; trap {sprung['name']} sprung"
            ticks = 0
            if "exhausted" in conditions_from_extra(ch.extra):
                ticks += 1
            campaign = self.campaigns.get(campaign_id)
            ticks += weather_travel_ticks(campaign.weather if campaign else "")
            if ticks:
                self._tick_character_vitals(character_id, ticks)
            self.db.flush()
            self.db.info.setdefault("pending_visuals", []).append(("location", loc.id))
            self._seed_world_rumors(campaign_id, character_id)
            return f"moved to {loc.name}{trap_note}"
        if action == "start_quest":
            q = self.quests.create(
                campaign_id,
                title=str(p["title"]),
                description=str(p.get("description", "")),
                character_id=character_id,
                reward_xp=int(p.get("reward_xp", 50)),
                reward_gold=int(p.get("reward_gold", 0)),
            )
            for i, obj in enumerate(p.get("objectives", [])):
                self.db.add(
                    QuestObjective(quest_id=q.id, description=str(obj), sort_order=i)
                )
            self.db.flush()
            self._seed_world_rumors(campaign_id, character_id)
            return f"quest started {q.title}"
        if action == "update_quest":
            q = self.quests.get(uuid.UUID(str(p["quest_id"])))
            if not q or q.campaign_id != campaign_id:
                raise ValueError("invalid quest")
            if "status" in p:
                q.status = str(p["status"])
            if "description" in p:
                q.description = str(p["description"])
            self.db.flush()
            return f"quest updated {q.id}"
        if action == "complete_quest":
            q = self.quests.get(uuid.UUID(str(p["quest_id"])))
            if not q or q.campaign_id != campaign_id:
                raise ValueError("invalid quest")
            extra = dict(q.extra or {})
            if q.status == "completed" or extra.get("rewarded"):
                raise ValueError("quest already completed")
            q.status = "completed"
            for obj in q.objectives:
                obj.is_completed = True
            extra["rewarded"] = True
            q.extra = extra
            self.gain_xp(character_id, max(0, q.reward_xp))
            ch = self.characters.get(character_id)
            if q.reward_gold:
                ch.gold += max(0, q.reward_gold)
            self.db.flush()
            return f"quest completed {q.title}"
        if action == "change_relationship":
            self.change_relationship(
                character_id,
                uuid.UUID(str(p["npc_id"])),
                trust_delta=float(p.get("trust_delta", 0)),
                fear_delta=float(p.get("fear_delta", 0)),
                respect_delta=float(p.get("respect_delta", 0)),
            )
            return "relationship updated"
        if action == "start_combat":
            self.start_combat(campaign_id, list(p.get("combatants", [])))
            notes: list[str] = []
            for _ in range(12):
                session = self.combat.active_for_campaign(campaign_id)
                current = self._current_fighter(session) if session else None
                if not current or self._is_player_combatant(current):
                    break
                note = self._enemy_act(campaign_id, character_id, current)
                if note:
                    notes.append(note)
                if session:
                    self._pass_turn(session)
            suffix = f"; {'; '.join(notes)}" if notes else ""
            return "combat started" + suffix
        if action == "end_combat":
            if not self.end_combat(
                campaign_id,
                character_id=character_id,
                reward_xp=int(p.get("reward_xp", 0)),
                reward_gold=int(p.get("reward_gold", 0)),
            ):
                raise ValueError("no active combat")
            return "combat ended"
        if action == "flee_combat":
            if not self.end_combat(campaign_id, character_id=character_id, reward_xp=0, reward_gold=0):
                raise ValueError("no active combat")
            return "fled combat"
        if action == "damage_combatant":
            msg = self.damage_combatant(
                campaign_id,
                uuid.UUID(str(p["combatant_id"])),
                int(p.get("amount", 0)),
                character_id=character_id,
            )
            self._wear_equipped_weapons(character_id)
            return msg
        if action == "advance_turn":
            return self.advance_turn(campaign_id, character_id=character_id)
        if action == "set_world_flag":
            campaign = self.campaigns.get(campaign_id)
            ws = dict(campaign.world_state or {})
            ws[str(p["key"])] = p.get("value")
            campaign.world_state = ws
            self.db.flush()
            return f"world_flag {p['key']}"
        if action == "lock_location":
            loc = self.locations.get(uuid.UUID(str(p["location_id"])))
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            extra = dict(loc.extra or {})
            extra["locked"] = True
            extra["unlocked"] = False
            loc.extra = extra
            self.db.flush()
            return f"locked {loc.name}"
        if action == "unlock_location":
            loc = self.locations.get(uuid.UUID(str(p["location_id"])))
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            extra = dict(loc.extra or {})
            extra["unlocked"] = True
            loc.extra = extra
            self.db.flush()
            return f"unlocked {loc.name}"
        if action == "set_time":
            campaign = self.campaigns.get(campaign_id)
            new_time = str(p["value"])
            if is_time_regression(campaign.current_time, new_time):
                raise ValueError("time cannot move backwards")
            old_ord = time_ordinal(campaign.current_time)
            new_ord = time_ordinal(new_time)
            campaign.current_time = new_time
            self.db.flush()
            if old_ord is not None and new_ord is not None and new_ord > old_ord:
                self._tick_character_vitals(character_id, new_ord - old_ord)
            self._tick_schedules(campaign_id)
            self._seed_world_rumors(campaign_id, character_id)
            return f"time={campaign.current_time}"
        if action == "advance_time":
            campaign = self.campaigns.get(campaign_id)
            steps = int(p.get("steps", 1) or 1)
            campaign.current_time = advance_world_time(campaign.current_time, steps)
            self.db.flush()
            self._tick_character_vitals(character_id, steps)
            self._tick_schedules(campaign_id)
            self._seed_world_rumors(campaign_id, character_id)
            return f"time={campaign.current_time}"
        if action == "set_weather":
            campaign = self.campaigns.get(campaign_id)
            value = str(p.get("value") or p.get("weather") or "").strip()[:64]
            if not value:
                raise ValueError("weather required")
            campaign.weather = value
            self.db.flush()
            return f"weather={campaign.weather}"
        if action == "learn_fact":
            fact = str(p.get("fact") or p.get("content") or "").strip()
            if not fact:
                raise ValueError("fact required")
            ch = self.characters.get(character_id)
            ch.extra = add_fact(ch.extra, fact)
            self.db.flush()
            return "fact learned"
        if action == "change_faction_rep":
            campaign = self.campaigns.get(campaign_id)
            campaign.world_state = faction_delta(
                campaign.world_state,
                str(p.get("faction") or ""),
                int(p.get("delta") or 0),
            )
            self.db.flush()
            return "faction updated"
        if action == "set_lighting":
            loc_id = p.get("location_id")
            loc = self.locations.get(uuid.UUID(str(loc_id))) if loc_id else None
            if loc is None:
                ch = self.characters.get(character_id)
                loc = self.locations.get(ch.location_id) if ch and ch.location_id else None
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            extra = dict(loc.extra or {})
            extra["lighting"] = lighting_of({"lighting": p.get("lighting") or p.get("value")})
            loc.extra = extra
            self.db.flush()
            return f"lighting={extra['lighting']}"
        if action == "unlock_container":
            loc = self._container_location(campaign_id, character_id, p)
            loc.extra = unlock_container(loc.extra, str(p.get("container_id") or p.get("id") or ""))
            self.db.flush()
            return "container unlocked"
        if action == "loot_container":
            loc = self._container_location(campaign_id, character_id, p)
            extra, items = loot_container(loc.extra, str(p.get("container_id") or p.get("id") or ""))
            loc.extra = extra
            for item in items:
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                self.add_item(
                    character_id,
                    campaign_id,
                    name,
                    quantity=int(item.get("quantity") or 1),
                    item_type=str(item.get("item_type") or "misc"),
                    description=str(item.get("description") or ""),
                    weight=int(item.get("weight") or 0),
                    properties=dict(item.get("properties") or {}),
                )
            self.db.flush()
            return f"looted {len(items)} item(s)"
        if action == "death_save":
            ch = self.characters.get(character_id)
            if self._is_dead(ch):
                raise ValueError("character is dead")
            if ch.hp > 0:
                raise ValueError("not dying")
            extra, outcome = record_death_save(ch.extra, success=bool(p.get("success")))
            ch.extra = extra
            if outcome == "dead":
                self._set_condition(ch, "dead")
            elif outcome == "stable":
                self._set_condition(ch, "stable")
            self.db.flush()
            return f"death_save={outcome}"
        if action == "set_combatant_cover":
            target = self._active_combatant(campaign_id, uuid.UUID(str(p["combatant_id"])))
            session = self.combat.active_for_campaign(campaign_id)
            self._require_own_turn(session, target)
            extra = dict(target.extra or {})
            extra["cover"] = cover_bonus({"cover": int(p.get("cover") or 0)})
            target.extra = extra
            self.db.flush()
            return f"cover={extra['cover']}"
        if action == "set_combatant_range":
            target = self._active_combatant(campaign_id, uuid.UUID(str(p["combatant_id"])))
            session = self.combat.active_for_campaign(campaign_id)
            self._require_own_turn(session, target)
            extra = dict(target.extra or {})
            extra["range_ft"] = max(0, int(p.get("range_ft") or p.get("range") or 5))
            target.extra = extra
            self.db.flush()
            return f"range={extra['range_ft']}"
        if action == "move_combatant":
            target = self._active_combatant(campaign_id, uuid.UUID(str(p["combatant_id"])))
            session = self.combat.active_for_campaign(campaign_id)
            self._require_own_turn(session, target)
            self._consume_act(session, "turn_moved")
            extra = dict(target.extra or {})
            x, y = cell_pos(extra)
            if "x" in p or "y" in p:
                x = clamp_cell(p.get("x", x))
                y = clamp_cell(p.get("y", y))
            else:
                dx = max(-1, min(1, int(p.get("dx") or 0)))
                dy = max(-1, min(1, int(p.get("dy") or 0)))
                x, y = clamp_cell(x + dx), clamp_cell(y + dy)
            extra["x"], extra["y"] = x, y
            target.extra = extra
            session = self.combat.active_for_campaign(campaign_id)
            if session:
                self._refresh_ranges(session.combatants)
            self.db.flush()
            return f"moved to {x},{y}"
        if action == "spot_trap":
            loc = self._container_location(campaign_id, character_id, p)
            loc.extra = spot_trap(loc.extra, str(p.get("trap_id") or p.get("id") or ""))
            self.db.flush()
            return "trap spotted"
        if action == "disarm_trap":
            loc = self._container_location(campaign_id, character_id, p)
            loc.extra = disarm_trap(loc.extra, str(p.get("trap_id") or p.get("id") or ""))
            self.db.flush()
            return "trap disarmed"
        if action == "trigger_trap":
            loc = self._container_location(campaign_id, character_id, p)
            extra, sprung = trigger_trap(loc.extra, str(p.get("trap_id") or p.get("id") or ""))
            loc.extra = extra
            self.apply_damage(
                character_id,
                sprung["damage"],
                damage_type=sprung.get("damage_type"),
            )
            self.db.flush()
            return f"trap {sprung['name']} sprung"
        if action == "hear_rumor":
            campaign = self.campaigns.get(campaign_id)
            ws, text = hear_rumor(
                campaign.world_state,
                rumor_id=p.get("rumor_id") or p.get("id"),
                text=p.get("text") or p.get("fact"),
            )
            campaign.world_state = ws
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(campaign, "world_state")
            ch = self.characters.get(character_id)
            ch.extra = add_fact(ch.extra, text)
            self.db.flush()
            return "rumor heard"
        if action == "share_knowledge":
            npc_id = p.get("npc_id")
            if not npc_id:
                raise ValueError("npc not here")
            npc = self.npcs.get(uuid.UUID(str(npc_id)))
            ch = self.characters.get(character_id)
            if not npc or npc.campaign_id != campaign_id or not npc.is_alive:
                raise ValueError("npc not here")
            if not ch or npc.location_id != ch.location_id:
                raise ValueError("npc not here")
            topic_id = str(p.get("topic_id") or p.get("id") or "").strip()
            text = packet_text(npc.knowledge, topic_id, npc.secrets)
            extra = add_fact(ch.extra, text)
            ch.extra = mark_heard_topic(extra, npc.id, topic_id)
            self.db.flush()
            return f"learned {topic_id}"
        if action == "save_checkpoint":
            if self.combat.active_for_campaign(campaign_id):
                raise ValueError("cannot save during combat")
            campaign = self.campaigns.get(campaign_id)
            payload = self._capture_checkpoint(campaign_id, character_id)
            campaign.world_state = upsert_checkpoint(
                campaign.world_state, str(p.get("name") or "camp"), payload
            )
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(campaign, "world_state")
            self.db.flush()
            return "checkpoint saved"
        if action == "load_checkpoint":
            if self.combat.active_for_campaign(campaign_id):
                raise ValueError("cannot load during combat")
            campaign = self.campaigns.get(campaign_id)
            payload = checkpoint_payload(campaign.world_state, str(p.get("name") or "camp"))
            self._restore_checkpoint(campaign_id, character_id, payload)
            return "checkpoint loaded"
        raise ValueError(f"Unhandled action {action}")

    def persist_events(
        self,
        *,
        campaign_id: uuid.UUID,
        character_id: uuid.UUID,
        location_id: uuid.UUID | None,
        proposed: list,
    ) -> list[str]:
        from app.game.event_types import ALL_EVENT_TYPES, DISCOVERY_MADE

        summaries = []
        for ev in proposed:
            event_type = ev.event_type if ev.event_type in ALL_EVENT_TYPES else DISCOVERY_MADE
            event = self.events.create(
                campaign_id=campaign_id,
                event_type=event_type,
                summary=ev.summary,
                character_id=character_id,
                location_id=location_id,
                payload=ev.payload,
                importance=ev.importance,
            )
            summaries.append(f"{event.event_type}: {event.summary}")
        return summaries

    def resolve_dice_requests(self, character_id: uuid.UUID, requests: list) -> list[DiceResultOut]:
        character = self.characters.get(character_id)
        results: list[DiceResultOut] = []
        for req in requests:
            if req.kind == "d20" or req.notation.lower().startswith("1d20") or req.skill:
                ability_name = "strength"
                skill_label = req.skill
                if req.skill:
                    ability_name = SKILL_TO_ABILITY.get(req.skill.lower(), req.skill.lower())
                ability = 10
                if character:
                    ability = int(getattr(character, ability_name, 10) or 10)
                roll = self.roll_d20()
                natural = roll.rolls[0] if roll.rolls else roll.total
                mod = ability_modifier(ability)
                if character and "exhausted" in conditions_from_extra(character.extra):
                    mod -= EXHAUSTED_CHECK_PENALTY
                if character:
                    camp = self.campaigns.get(character.campaign_id)
                    if camp:
                        mod -= weather_check_penalty(camp.weather)
                total = natural + mod
                success = total >= req.dc if req.dc is not None else total >= 12
                critical = None
                if natural == 20:
                    critical = "natural_20"
                elif natural == 1:
                    critical = "natural_1"
                results.append(
                    DiceResultOut(
                        notation="1d20",
                        total=total,
                        rolls=[natural],
                        purpose=req.purpose or req.skill or "",
                        success=success,
                        ability=ability_name,
                        skill=skill_label,
                        modifier=mod,
                        dc=req.dc if req.dc is not None else 12,
                        natural=natural,
                        critical=critical,
                    )
                )
            else:
                roll = self.roll_dice(req.notation)
                results.append(
                    DiceResultOut(
                        notation=req.notation,
                        total=roll.total,
                        rolls=roll.rolls,
                        purpose=req.purpose,
                        modifier=roll.modifier,
                        natural=roll.rolls[0] if len(roll.rolls) == 1 else None,
                    )
                )
        return results
