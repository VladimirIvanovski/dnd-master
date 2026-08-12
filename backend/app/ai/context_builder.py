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
        npc_lines = ", ".join(
            f"{n.name}" + (f" — {n.title}" if n.title else "") for n in state.nearby_npcs
        ) or "none"
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
        }

        user_prompt = f"""Campaign: {state.campaign_name}
Tone: {tone or "(establish a consistent tone)"}
Themes: {theme_line or "(none)"}
Time: {state.current_time} | Weather: {state.weather}
World flags: { {k: v for k, v in ws.items() if k not in excluded_flags} }
Narrative meta: turn={narrative.get("turn", 0)} last_described_scene={narrative.get("last_described_scene_id")} recent_event_types={narrative.get("recent_event_types")}

{dna_block}

Character: {ch.name}, Level {ch.level} {ch.race} {ch.class_name}
HP {ch.hp}/{ch.max_hp} AC {ch.ac} XP {ch.xp}
Coins: {ch.gold} gp, {getattr(ch, 'silver', 0)} sp, {getattr(ch, 'copper', 0)} cp
Abilities: {ch.abilities}

Location: {loc_line}
Nearby NPCs: {npc_lines}
Active quests: {quest_lines}
Inventory: {inv}
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
    def _combat_block(state: GameState) -> str:
        if not state.combat:
            return "none"
        lines = [
            f"ACTIVE round={state.combat.round_number} status={state.combat.status}",
            "Combatants:",
        ]
        for c in state.combat.combatants:
            lines.append(
                f"- id={c.id} name={c.name} type={c.combatant_type} "
                f"hp={c.hp}/{c.max_hp} ac={c.ac} initiative={c.initiative}"
            )
        lines.append(
            "When the player is hurt, use apply_damage. When an enemy is hurt, use damage_combatant with their id."
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
