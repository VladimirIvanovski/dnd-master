from __future__ import annotations

from app.ai.prompts.system import SYSTEM_PROMPT
from app.game.campaign_dna import format_dna_for_prompt
from app.schemas.gameplay import DiceResultOut
from app.schemas.state import GameState


class ContextBuilder:
    def build(
        self,
        *,
        state: GameState,
        player_action: str,
        recent_events: list[str],
        memories: list[str],
        recent_conversation: list[str] | None = None,
        event_director_note: str | None = None,
        environment_note: str | None = None,
        dice_results: list[DiceResultOut] | None = None,
        rewrite_pass: bool = False,
    ) -> tuple[str, str]:
        location = state.current_location
        loc_line = (
            f"{location.name} ({location.location_type}): {location.description}"
            if location
            else "Unknown location"
        )
        npc_lines = "; ".join(self._npc_line(n) for n in state.nearby_npcs) or "none"
        quest_lines = "; ".join(
            f"{q.title} [{q.status}]" for q in state.active_quests
        ) or "none"
        inv = ", ".join(f"{i.name} x{i.quantity}" for i in state.inventory[:12]) or "empty"
        ch = state.character
        ws = state.world_state or {}
        tone = str(ws.get("tone") or "")
        themes = ws.get("themes") or []
        theme_line = ", ".join(str(t) for t in themes) if isinstance(themes, list) else str(themes)
        narrative = ws.get("narrative") if isinstance(ws.get("narrative"), dict) else {}
        dna = ws.get("campaign_dna") if isinstance(ws.get("campaign_dna"), dict) else None
        user_desc = str(ws.get("user_campaign_description") or "")
        dna_block = format_dna_for_prompt(dna, user_desc)

        dice_block = self._dice_block(dice_results)
        rewrite_line = ""
        if rewrite_pass:
            rewrite_line = (
                "REWRITE PASS: Dice are already resolved by the server. "
                "Narrate SUCCESS or FAILURE only in short plain DM speech — never quote totals, natural rolls, modifiers, or DCs. "
                "Use blank lines between short paragraphs. Leave dice_requests empty. Do not invent different outcomes.\n"
            )

        excluded_flags = {
            "tone",
            "themes",
            "opening_narration",
            "starting_location_id",
            "narrative",
            "campaign_dna",
            "user_campaign_description",
            "opening_delivered",
            "factions",
            "rumors",
        }

        user_prompt = f"""Campaign: {state.campaign_name}
Tone: {tone or "(establish a consistent tone)"}
Themes: {theme_line or "(none)"}
Time: {state.current_time} | Weather: {state.weather}
World flags: { {k: v for k, v in ws.items() if k not in excluded_flags} }
Narrative meta: turn={narrative.get("turn", 0)} last_described_scene={narrative.get("last_described_scene_id")} recent_event_types={narrative.get("recent_event_types")}

{dna_block}

Character: {ch.name}, Level {ch.level} {ch.race} {ch.class_name}
HP {ch.hp}/{ch.max_hp} (temp {getattr(ch, 'temp_hp', 0)}) AC {ch.ac} XP {ch.xp}
Conditions: {", ".join(ch.conditions) or "none"}
Stamina {ch.stamina}/100 Hunger {ch.hunger}/100 Thirst {ch.thirst}/100
Carry {ch.carry_weight}/{ch.carry_capacity}
Coins: {ch.gold} gp, {getattr(ch, 'silver', 0)} sp, {getattr(ch, 'copper', 0)} cp
Abilities: {ch.abilities}

Location: {loc_line}
Lighting: {getattr(location, "lighting", "daylight") if location else "unknown"}
Containers: {self._container_line(location)}
Spotted traps: {self._trap_line(location)}
Nearby NPCs: {npc_lines}
Active quests: {quest_lines}
Inventory: {inv}
Known facts (player knowledge only — do not invent or leak other secrets): {", ".join(ch.known_facts) or "none"}
Heard rumors: {", ".join(getattr(state, "heard_rumors", None) or []) or "none"}
Unheard rumor ids (hear_rumor with rumor_id if they actually overhear gossip — never invent the text): {", ".join(getattr(state, "unheard_rumor_ids", None) or []) or "none"}
Known places: {self._place_line(state)}
Factions: {state.factions or (ws.get("factions") if isinstance(ws.get("factions"), dict) else {}) or "none"}
Combat: {self._combat_block(state)}

{environment_note or ""}
{event_director_note or ""}
{rewrite_line}{dice_block}
Relevant memories:
{self._bullets(memories)}

Recent events:
{self._bullets(recent_events)}

Recent conversation:
{self._bullets(recent_conversation or [])}

Player action: {player_action}

Respond with JSON for DMResponse schema. Include exactly 3 suggested_actions grounded in what is actually available. Keep normal narration short (1–5 sentences), plain human-DM speech, blank lines between short paragraphs, sparse **bold** for key names/items/places. On new scenes: clear Location → concrete atmosphere → nearby → situation → room to act. Refuse impossible actions briefly. Persist quests/combat/damage/XP when fiction requires it.
"""
        return SYSTEM_PROMPT, user_prompt

    @staticmethod
    def _npc_line(npc) -> str:
        label = f"{npc.name}" + (f" — {npc.title}" if npc.title else "")
        if getattr(npc, "faction", ""):
            label += f" [{npc.faction}]"
        stock = getattr(npc, "stock", None) or []
        if stock:
            goods = ", ".join(
                f"{s.name} x{s.quantity} {s.price}gp" for s in stock[:6]
            )
            label += f" (sells {goods})"
        topics = getattr(npc, "topics", None) or []
        if topics:
            asked = {str(a).lower() for a in (getattr(npc, "asked", None) or [])}
            bits = []
            for t in topics[:6]:
                mark = "asked" if str(t.id).lower() in asked else "unasked"
                bits.append(f"{t.id}:{t.label} [{mark}]")
            label += f" topics: {', '.join(bits)}"
        trust = float(getattr(npc, "trust", 0) or 0)
        fear = float(getattr(npc, "fear", 0) or 0)
        respect = float(getattr(npc, "respect", 0) or 0)
        if trust or fear or respect:
            label += f" (trust {int(trust)} fear {int(fear)} respect {int(respect)})"
        return label

    @staticmethod
    def _container_line(location) -> str:
        if not location:
            return "none"
        boxes = getattr(location, "containers", None) or []
        if not boxes:
            return "none"
        return "; ".join(
            f"{b.name} [{'locked' if b.locked else 'open'}]" for b in boxes
        )

    @staticmethod
    def _trap_line(location) -> str:
        if not location:
            return "none"
        traps = getattr(location, "traps", None) or []
        if not traps:
            return "none"
        return "; ".join(
            f"{t.name} [{'armed' if t.armed else 'disarmed'}]" for t in traps
        )

    @staticmethod
    def _place_line(state: GameState) -> str:
        places = getattr(state, "known_locations", None) or []
        if not places:
            return "none"
        return "; ".join(
            f"{p.name} [{p.location_type}]" + (" (here)" if p.here else "") for p in places[:12]
        )

    @staticmethod
    def _combat_block(state: GameState) -> str:
        if not state.combat:
            return "none"
        lines = [
            f"ACTIVE round={state.combat.round_number} status={state.combat.status} "
            f"whose_turn={getattr(state.combat, 'whose_turn', '') or 'unknown'}",
            "Combatants:",
        ]
        for c in state.combat.combatants:
            lines.append(
                f"- id={c.id} name={c.name} type={c.combatant_type} "
                f"hp={c.hp}/{c.max_hp} ac={c.ac} initiative={c.initiative} "
                f"cover={getattr(c, 'cover', 0)} range_ft={getattr(c, 'range_ft', 5)} "
                f"pos={getattr(c, 'x', 3)},{getattr(c, 'y', 3)}"
            )
        lines.append(
            "move_combatant/damage_combatant only if whose_turn is that combatant (player attacks on the player's turn). "
            "Do not apply_damage for enemy strikes the engine already resolved."
        )
        return "\n".join(lines)

    @staticmethod
    def _dice_block(dice_results: list[DiceResultOut] | None) -> str:
        if not dice_results:
            return ""
        lines = [
            "Resolved dice rolls (authoritative):",
            "Narrate SUCCESS/FAILURE in fiction only — NEVER quote numbers, totals, DCs, or 'natural 20' in narration.",
        ]
        for d in dice_results:
            crit = f" critical={d.critical}" if d.critical else ""
            suc = (
                " SUCCESS"
                if d.success is True
                else " FAILURE"
                if d.success is False
                else ""
            )
            lines.append(
                f"- {d.purpose or d.notation}: natural={d.natural} rolls={d.rolls} "
                f"modifier={d.modifier} total={d.total} dc={d.dc}{suc}{crit} "
                f"ability={d.ability} skill={d.skill}"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _bullets(items: list[str], limit: int = 8) -> str:
        if not items:
            return "- (none)"
        return "\n".join(f"- {x}" for x in items[:limit])
