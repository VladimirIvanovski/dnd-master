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
from app.game.dice import ability_modifier, roll_dice, roll_d20, skill_check
from app.schemas.gameplay import DiceResultOut, StateChange
from app.utils.ids import utcnow

XP_THRESHOLDS = [0, 300, 900, 2700, 6500, 14000]
MAX_GOLD_GAIN = 200
MAX_ITEM_QTY = 99

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
        "remove_item",
        "gain_xp",
        "gain_gold",
        "spend_gold",
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
    }

    def __init__(self, db: Session, rng: random.Random | None = None):
        self.db = db
        self.rng = rng or random.Random()
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

    def apply_damage(self, character_id: uuid.UUID, amount: int) -> int:
        character = self.characters.get(character_id)
        if not character or amount < 0:
            raise ValueError("Invalid damage")
        character.hp = max(0, character.hp - amount)
        self.db.flush()
        return character.hp

    def heal(self, character_id: uuid.UUID, amount: int) -> int:
        character = self.characters.get(character_id)
        if not character or amount < 0:
            raise ValueError("Invalid heal")
        character.hp = min(character.max_hp, character.hp + amount)
        self.db.flush()
        return character.hp

    def add_item(self, character_id: uuid.UUID, campaign_id: uuid.UUID, name: str, quantity: int = 1, **kwargs):
        return self.inventory.add_item(character_id, campaign_id, name, quantity=quantity, **kwargs)

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
        for c in combatants:
            built.append(
                Combatant(
                    session_id=session.id,
                    name=c["name"],
                    combatant_type=c.get("combatant_type", "enemy"),
                    ref_id=c.get("ref_id"),
                    initiative=int(c.get("initiative", self.roll_d20().total)),
                    hp=c.get("hp", 10),
                    max_hp=c.get("max_hp", c.get("hp", 10)),
                    ac=c.get("ac", 10),
                )
            )
        built.sort(key=lambda x: x.initiative, reverse=True)
        for c in built:
            self.db.add(c)
        session.extra = {**(session.extra or {}), "turn_index": 0}
        self.db.flush()
        return session

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

    def damage_combatant(self, campaign_id: uuid.UUID, combatant_id: uuid.UUID, amount: int) -> str:
        if amount < 0:
            raise ValueError("Invalid damage")
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            raise ValueError("no active combat")
        target = next((c for c in session.combatants if c.id == combatant_id), None)
        if not target or not target.is_active:
            raise ValueError("combatant not found")
        target.hp = max(0, target.hp - amount)
        if target.hp <= 0:
            target.is_active = False
            return f"{target.name} defeated"
        self.db.flush()
        return f"{target.name} hp={target.hp}"

    def advance_turn(self, campaign_id: uuid.UUID) -> str:
        session = self.combat.active_for_campaign(campaign_id)
        if not session:
            raise ValueError("no active combat")
        active = [c for c in session.combatants if c.is_active]
        if not active:
            self.end_combat(campaign_id)
            return "combat ended — no active combatants"
        active.sort(key=lambda c: c.initiative, reverse=True)
        idx = int((session.extra or {}).get("turn_index", 0))
        idx = (idx + 1) % len(active)
        if idx == 0:
            session.round_number += 1
        session.extra = {**(session.extra or {}), "turn_index": idx}
        self.db.flush()
        current = active[idx]
        return f"round {session.round_number} turn: {current.name}"
    def apply_state_changes(
        self,
        *,
        campaign_id: uuid.UUID,
        character_id: uuid.UUID,
        changes: list[StateChange],
    ) -> ApplyResult:
        result = ApplyResult()
        for change in changes:
            try:
                msg = self._apply_one(campaign_id, character_id, change)
                result.applied.append(msg)
            except Exception as exc:  # noqa: BLE001 — validate proposals
                result.rejected.append(f"{change.action}: {exc}")
        return result

    def _apply_one(
        self, campaign_id: uuid.UUID, character_id: uuid.UUID, change: StateChange
    ) -> str:
        action = change.action
        p = change.params
        if action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Unknown action {action}")

        if action == "apply_damage":
            hp = self.apply_damage(character_id, int(p.get("amount", 0)))
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
            self.add_item(
                character_id,
                campaign_id,
                name,
                quantity=qty,
                item_type=str(p.get("item_type", "misc")),
                description=str(p.get("description", "")),
            )
            return f"added item {name}"
        if action == "remove_item":
            ok = self.remove_item(character_id, uuid.UUID(str(p["item_id"])), int(p.get("quantity", 1)))
            if not ok:
                raise ValueError("item not found")
            return f"removed item {p['item_id']}"
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
            if not title or not personality:
                from app.utils.npc_variety import random_npc_seed

                flavor = random_npc_seed(avoid_names={name})
                title = title or flavor.title
                personality = personality or flavor.personality
                goals = goals or flavor.goals
            npc = self.npcs.create(
                campaign_id,
                name=name,
                location_id=location_id,
                title=title,
                personality=personality,
                goals=goals,
            )
            return f"npc spawned {npc.name}"
        if action == "update_npc":
            npc = self.npcs.get(uuid.UUID(str(p["npc_id"])))
            if not npc or npc.campaign_id != campaign_id:
                raise ValueError("invalid npc")
            for key in ("title", "personality", "goals", "fears", "motivations", "faction"):
                if key in p:
                    setattr(npc, key, str(p[key]))
            if "location_id" in p and p["location_id"]:
                npc.location_id = uuid.UUID(str(p["location_id"]))
            if "is_alive" in p:
                npc.is_alive = bool(p["is_alive"])
            self.db.flush()
            return f"npc updated {npc.name}"
        if action == "gain_xp":
            amount = int(p.get("amount", 0))
            if amount < 0 or amount > 500:
                raise ValueError("invalid XP amount")
            xp, level = self.gain_xp(character_id, amount)
            return f"xp={xp} level={level}"
        if action == "gain_gold":
            amount = int(p.get("amount", 0))
            if amount <= 0:
                raise ValueError("gold gain must be positive")
            if amount > MAX_GOLD_GAIN:
                raise ValueError(f"gold gain exceeds max {MAX_GOLD_GAIN}")
            ch = self.characters.get(character_id)
            ch.gold += amount
            self.db.flush()
            return f"gold={ch.gold}"
        if action == "spend_gold":
            ch = self.characters.get(character_id)
            amount = int(p.get("amount", 0))
            if amount <= 0:
                raise ValueError("gold spend must be positive")
            if ch.gold < amount:
                raise ValueError("not enough gold")
            ch.gold -= amount
            self.db.flush()
            return f"gold={ch.gold}"
        if action == "move_to_location":
            loc_id = uuid.UUID(str(p["location_id"]))
            loc = self.locations.get(loc_id)
            if not loc or loc.campaign_id != campaign_id:
                raise ValueError("invalid location")
            ch = self.characters.get(character_id)
            ch.location_id = loc_id
            self.db.flush()
            return f"moved to {loc.name}"
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
            q.status = "completed"
            for obj in q.objectives:
                obj.is_completed = True
            self.gain_xp(character_id, q.reward_xp)
            ch = self.characters.get(character_id)
            ch.gold += q.reward_gold
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
            return "combat started"
        if action == "end_combat":
            if not self.end_combat(
                campaign_id,
                character_id=character_id,
                reward_xp=int(p.get("reward_xp", 0)),
                reward_gold=int(p.get("reward_gold", 0)),
            ):
                raise ValueError("no active combat")
            return "combat ended"
        if action == "damage_combatant":
            return self.damage_combatant(
                campaign_id,
                uuid.UUID(str(p["combatant_id"])),
                int(p.get("amount", 0)),
            )
        if action == "advance_turn":
            return self.advance_turn(campaign_id)
        if action == "set_world_flag":
            campaign = self.campaigns.get(campaign_id)
            ws = dict(campaign.world_state or {})
            ws[str(p["key"])] = p.get("value")
            campaign.world_state = ws
            self.db.flush()
            return f"world_flag {p['key']}"
        if action == "set_time":
            campaign = self.campaigns.get(campaign_id)
            campaign.current_time = str(p["value"])
            self.db.flush()
            return f"time={campaign.current_time}"
        if action == "set_weather":
            campaign = self.campaigns.get(campaign_id)
            campaign.weather = str(p["value"])
            self.db.flush()
            return f"weather={campaign.weather}"
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
                if req.skill:
                    ability_name = SKILL_TO_ABILITY.get(req.skill.lower(), req.skill.lower())
                ability = 10
                if character:
                    ability = getattr(character, ability_name, 10)
                roll = self.roll_d20()
                total = roll.total + ability_modifier(ability)
                success = total >= req.dc if req.dc is not None else None
                results.append(
                    DiceResultOut(
                        notation="1d20",
                        total=total,
                        rolls=roll.rolls,
                        purpose=req.purpose or req.skill or "",
                        success=success,
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
                    )
                )
        return results
