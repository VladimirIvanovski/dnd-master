from __future__ import annotations

from app.ai.prompts.system import SYSTEM_PROMPT
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
    ) -> tuple[str, str]:
        location = state.current_location
        loc_line = (
            f"{location.name}: {location.description}" if location else "Unknown location"
        )
        npc_lines = ", ".join(n.name for n in state.nearby_npcs) or "none"
        quest_lines = "; ".join(
            f"{q.title} [{q.status}]" for q in state.active_quests
        ) or "none"
        inv = ", ".join(f"{i.name} x{i.quantity}" for i in state.inventory[:12]) or "empty"
        ch = state.character
        ws = state.world_state or {}
        tone = str(ws.get("tone") or "")
        themes = ws.get("themes") or []
        theme_line = ", ".join(str(t) for t in themes) if isinstance(themes, list) else str(themes)

        user_prompt = f"""Campaign: {state.campaign_name}
Tone: {tone or "(establish a consistent tone)"}
Themes: {theme_line or "(none)"}
Time: {state.current_time} | Weather: {state.weather}
World flags: { {k: v for k, v in ws.items() if k not in {"tone", "themes", "opening_narration", "starting_location_id"}} }

Character: {ch.name}, Level {ch.level} {ch.race} {ch.class_name}
HP {ch.hp}/{ch.max_hp} AC {ch.ac} Gold {ch.gold} XP {ch.xp}
Abilities: {ch.abilities}

Location: {loc_line}
Nearby NPCs: {npc_lines}
Active quests: {quest_lines}
Inventory: {inv}
Combat: {"active" if state.combat else "none"}

Relevant memories:
{self._bullets(memories)}

Recent events:
{self._bullets(recent_events)}

Recent conversation:
{self._bullets(recent_conversation or [])}

Player action: {player_action}

Respond with JSON for DMResponse schema. Keep narration aligned with the campaign tone.
"""
        return SYSTEM_PROMPT, user_prompt

    @staticmethod
    def _bullets(items: list[str], limit: int = 8) -> str:
        if not items:
            return "- (none)"
        return "\n".join(f"- {x}" for x in items[:limit])
