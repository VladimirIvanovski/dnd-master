from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.ai.dm_service import DMService
from app.ai.factory import get_llm_provider
from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import DialogueLine, GameplayResponse, PlayerActionRequest, StateChange
from app.schemas.state import GameState
from app.services.memory import MemoryService
from app.utils.npc_variety import random_npc_seed

logger = logging.getLogger(__name__)

_IGNORED_SPEAKERS = {
    "you",
    "player",
    "narrator",
    "dm",
    "dungeon master",
    "system",
}


class GameplayService:
    """Core player-action pipeline. API routes must stay thin."""

    def __init__(
        self,
        db: Session,
        *,
        dm: DMService | None = None,
        engine: GameEngine | None = None,
        memory: MemoryService | None = None,
    ):
        self.db = db
        self.loader = GameStateLoader(db)
        self.engine = engine or GameEngine(db)
        self.memory = memory or MemoryService(db)
        self.dm = dm or DMService(get_llm_provider())

    def get_state(self, campaign_id, character_id):
        return self.loader.load(campaign_id, character_id)

    def handle_action(self, request: PlayerActionRequest) -> GameplayResponse:
        state = self.loader.load(request.campaign_id, request.character_id)
        recent_events = self.memory.short_term(request.campaign_id)
        memories = self.memory.retrieve(state, request.action)

        dm_out = self.dm.narrate(
            state=state,
            player_action=request.action,
            recent_events=recent_events,
            memories=memories,
            recent_conversation=recent_events[:6],
        )

        dice_results = self.engine.resolve_dice_requests(
            request.character_id, dm_out.dice_requests
        )

        changes = self._gate_changes(dm_out.state_changes, dice_results)
        changes.extend(self._quest_updates_as_changes(dm_out.quest_updates))
        changes.extend(self._npc_updates_as_changes(state, dm_out.npc_updates))
        changes.extend(self._dialogue_npcs_as_changes(state, dm_out.dialogue))

        apply_result = self.engine.apply_state_changes(
            campaign_id=request.campaign_id,
            character_id=request.character_id,
            changes=changes,
        )
        location_id = state.current_location.id if state.current_location else None
        event_summaries = self.engine.persist_events(
            campaign_id=request.campaign_id,
            character_id=request.character_id,
            location_id=location_id,
            proposed=dm_out.events,
        )
        apply_result.event_summaries = event_summaries
        apply_result.dice_results = dice_results

        narration = dm_out.narration
        if dice_results:
            bits = []
            for d in dice_results:
                bit = f"[{d.purpose or d.notation}: {d.total}"
                if d.success is True:
                    bit += " — success"
                elif d.success is False:
                    bit += " — failure"
                bit += "]"
                bits.append(bit)
            narration = f"{narration}\n\n{' '.join(bits)}"

        for candidate in dm_out.memory_candidates:
            self.memory.store_candidate(
                request.campaign_id,
                candidate.content,
                importance=candidate.importance,
                entity_ids=candidate.entity_ids,
                location_id=location_id,
            )

        self.db.commit()
        refreshed = self.loader.load(request.campaign_id, request.character_id)

        return GameplayResponse(
            narration=narration,
            dialogue=dm_out.dialogue,
            dice_results=dice_results,
            applied_events=event_summaries,
            applied_changes=apply_result.applied,
            rejected_changes=apply_result.rejected,
            state_snapshot=refreshed.model_dump(mode="json"),
        )

    @staticmethod
    def _gate_changes(changes: list[StateChange], dice_results: list) -> list[StateChange]:
        if not changes:
            return []
        any_fail = any(d.success is False for d in dice_results)
        any_success = any(d.success is True for d in dice_results)
        has_check = any(d.success is not None for d in dice_results)
        gated: list[StateChange] = []
        for change in changes:
            requires = bool(change.params.get("requires_success"))
            if requires and has_check:
                if any_fail and not any_success:
                    continue
                if not any_success:
                    continue
            gated.append(change)
        return gated

    @staticmethod
    def _quest_updates_as_changes(updates: list) -> list[StateChange]:
        out: list[StateChange] = []
        for u in updates:
            if u.new_quest:
                out.append(StateChange(action="start_quest", params=u.new_quest))
            elif u.quest_id and u.status == "completed":
                out.append(StateChange(action="complete_quest", params={"quest_id": str(u.quest_id)}))
            elif u.quest_id:
                params = {"quest_id": str(u.quest_id)}
                if u.status:
                    params["status"] = u.status
                out.append(StateChange(action="update_quest", params=params))
        return out

    @staticmethod
    def _npc_updates_as_changes(state: GameState, updates: list) -> list[StateChange]:
        out: list[StateChange] = []
        loc_id = str(state.current_location.id) if state.current_location else None
        for u in updates:
            if u.npc_id:
                params = {"npc_id": str(u.npc_id), **(u.changes or {})}
                out.append(StateChange(action="update_npc", params=params))
            elif u.name:
                params = {
                    "name": u.name,
                    "location_id": loc_id,
                    **(u.changes or {}),
                }
                out.append(StateChange(action="spawn_npc", params=params))
        return out

    @staticmethod
    def _dialogue_npcs_as_changes(
        state: GameState, dialogue: list[DialogueLine]
    ) -> list[StateChange]:
        known = {n.name.lower() for n in state.nearby_npcs}
        known.add(state.character.name.lower())
        known |= _IGNORED_SPEAKERS
        loc_id = str(state.current_location.id) if state.current_location else None
        out: list[StateChange] = []
        for line in dialogue:
            name = (line.speaker or "").strip()
            if not name or name.lower() in known:
                continue
            known.add(name.lower())
            flavor = random_npc_seed(avoid_names=known)
            out.append(
                StateChange(
                    action="spawn_npc",
                    params={
                        "name": name,
                        "location_id": loc_id,
                        "title": flavor.title,
                        "personality": flavor.personality,
                        "goals": flavor.goals,
                    },
                )
            )
        return out
