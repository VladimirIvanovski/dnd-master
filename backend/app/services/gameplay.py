from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.ai.dm_service import DMService
from app.ai.factory import get_llm_provider
from app.game.engine import GameEngine
from app.game.event_director import EventDirector, format_suggestion_for_prompt
from app.game.scene_context import (
    environment_guidance,
    get_narrative_meta,
    next_narrative_meta,
    should_describe_environment,
)
from app.game.state import GameStateLoader
from app.schemas.gameplay import DialogueLine, GameplayResponse, PlayerActionRequest, StateChange
from app.schemas.state import GameState
from app.services.dialogue_dedupe import strip_embedded_dialogue
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

_FALLBACK_SUGGESTIONS = [
    "Look around carefully",
    "Explore a path nearby",
    "Check your belongings",
]


def _normalize_suggestions(
    raw: list[str] | None,
    *,
    has_nearby_npcs: bool = False,
) -> list[str]:
    out: list[str] = []
    for item in raw or []:
        text = " ".join(str(item).split()).strip()
        if not text:
            continue
        if not has_nearby_npcs and text.lower().startswith("talk to"):
            continue
        if text not in out:
            out.append(text[:160])
        if len(out) >= 3:
            break
    fallbacks = list(_FALLBACK_SUGGESTIONS)
    if has_nearby_npcs:
        fallbacks = [
            "Look around carefully",
            "Talk to someone nearby",
            "Check your belongings",
        ]
    while len(out) < 3:
        for fb in fallbacks:
            if fb not in out:
                out.append(fb)
            if len(out) >= 3:
                break
    return out[:3]


class GameplayService:
    """Core player-action pipeline. API routes must stay thin."""

    def __init__(
        self,
        db: Session,
        *,
        dm: DMService | None = None,
        engine: GameEngine | None = None,
        memory: MemoryService | None = None,
        event_director: EventDirector | None = None,
    ):
        self.db = db
        self.loader = GameStateLoader(db)
        self.engine = engine or GameEngine(db)
        self.memory = memory or MemoryService(db)
        self.dm = dm or DMService(get_llm_provider())
        self.event_director = event_director or EventDirector()

    def get_state(self, campaign_id, character_id):
        return self.loader.load(campaign_id, character_id)

    def scene_history(self, campaign_id, character_id, *, limit: int = 40) -> list[dict]:
        """Oldest-first beats for rebuilding the UI scene log on Continue."""
        from app.game.event_types import PLAYER_ACTION, SCENE_NARRATION

        rows = self.memory.events.recent(
            campaign_id, limit=max(limit * 2, 40), character_id=character_id
        )
        rows = list(reversed(rows))
        chat = [e for e in rows if e.event_type in {PLAYER_ACTION, SCENE_NARRATION}]
        chosen = chat[-limit:] if chat else rows[-limit:]
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "summary": e.summary,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in chosen
        ]

    def handle_action(self, request: PlayerActionRequest) -> GameplayResponse:
        state = self.loader.load(request.campaign_id, request.character_id)
        recent_events = self.memory.short_term(request.campaign_id)
        memories = self.memory.retrieve(state, request.action)
        meta = get_narrative_meta(state.world_state)
        describe_env = should_describe_environment(state, meta, request.action)
        env_note = environment_guidance(describe_env, state, meta)

        suggestion = self.event_director.suggest(
            state,
            player_action=request.action,
            narrative_meta=meta,
        )
        director_note = format_suggestion_for_prompt(suggestion)

        # Pass 1: DM may request dice (and/or narrate if no check).
        dm_out = self.dm.narrate(
            state=state,
            player_action=request.action,
            recent_events=recent_events,
            memories=memories,
            recent_conversation=recent_events[:6],
            event_director_note=director_note,
            environment_note=env_note,
        )

        dice_results = self.engine.resolve_dice_requests(
            request.character_id, dm_out.dice_requests
        )

        # Pass 2 (same HTTP request): if checks were requested, roll first then
        # rewrite narration with authoritative results — no second client call.
        if dice_results:
            dm_out = self.dm.narrate(
                state=state,
                player_action=request.action,
                recent_events=recent_events,
                memories=memories,
                recent_conversation=recent_events[:6],
                event_director_note=director_note,
                environment_note=env_note,
                dice_results=dice_results,
                rewrite_pass=True,
            )

        changes = self._gate_changes(dm_out.state_changes, dice_results)
        changes.extend(self._quest_updates_as_changes(dm_out.quest_updates))
        changes.extend(self._npc_updates_as_changes(state, dm_out.npc_updates))
        changes.extend(self._dialogue_npcs_as_changes(state, dm_out.dialogue))
        changes = self._mechanical_fallbacks(state, request, dice_results, changes)

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

        narration = strip_embedded_dialogue(dm_out.narration, dm_out.dialogue)

        fired_id = suggestion.archetype.id if suggestion.fire and suggestion.archetype else None
        fired_cat = (
            suggestion.archetype.category if suggestion.fire and suggestion.archetype else None
        )
        # Cooldown advances whenever a random beat was *offered*, so we never spam every turn.
        new_meta = next_narrative_meta(
            meta,
            state=state,
            described=describe_env,
            fired_event_id=fired_id,
            fired_category=fired_cat,
        )
        self._persist_narrative_meta(request.campaign_id, new_meta)

        for candidate in dm_out.memory_candidates:
            # Prefer meaningful memories (importance >= 4 already filtered in store)
            self.memory.store_candidate(
                request.campaign_id,
                candidate.content,
                importance=candidate.importance,
                entity_ids=candidate.entity_ids,
                location_id=location_id,
            )

        from app.game.event_types import PLAYER_ACTION, SCENE_NARRATION

        self.memory.events.create(
            request.campaign_id,
            PLAYER_ACTION,
            request.action[:1000],
            character_id=request.character_id,
            location_id=location_id,
            payload={"kind": "player"},
            importance=3,
        )
        if narration.strip():
            self.memory.events.create(
                request.campaign_id,
                SCENE_NARRATION,
                narration[:4000],
                character_id=request.character_id,
                location_id=location_id,
                payload={"kind": "narration"},
                importance=5,
            )

        orch = self._flush_pending_visuals()
        self.db.commit()
        if orch:
            orch.kick_workers_after_commit()
        refreshed = self.loader.load(request.campaign_id, request.character_id)

        return GameplayResponse(
            narration=narration,
            dialogue=dm_out.dialogue,
            dice_results=dice_results,
            applied_events=event_summaries,
            applied_changes=apply_result.applied,
            rejected_changes=apply_result.rejected,
            state_snapshot=refreshed.model_dump(mode="json"),
            suggested_actions=_normalize_suggestions(
                dm_out.suggested_actions,
                has_nearby_npcs=bool(refreshed.nearby_npcs),
            ),
        )

    def _persist_narrative_meta(self, campaign_id, meta: dict) -> None:
        campaign = self.engine.campaigns.get(campaign_id)
        if not campaign:
            return
        ws = dict(campaign.world_state or {})
        ws["narrative"] = meta
        campaign.world_state = ws
        self.db.flush()

    def _flush_pending_visuals(self):
        pending = list(self.db.info.pop("pending_visuals", []))
        if not pending:
            return None
        from app.database.models import Character, Item, Location, NPC
        from app.visual import VisualOrchestrator

        orch = VisualOrchestrator(self.db)
        for kind, entity_id in pending:
            if kind == "location":
                loc = self.db.get(Location, entity_id)
                if loc:
                    orch.on_location_created(loc)
            elif kind == "npc":
                npc = self.db.get(NPC, entity_id)
                if npc:
                    orch.on_npc_created(npc)
            elif kind == "item":
                item = self.db.get(Item, entity_id)
                if item:
                    orch.on_item_created(item)
            elif kind == "character":
                ch = self.db.get(Character, entity_id)
                if ch:
                    orch.on_character_created(ch)
        return orch

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
    def _mechanical_fallbacks(
        state: GameState,
        request: PlayerActionRequest,
        dice_results: list,
        changes: list[StateChange],
    ) -> list[StateChange]:
        """Light nets when the DM narrates acceptance/hurt but forgets state_changes."""
        out = list(changes)
        action = (request.action or "").lower()
        actions_set = {c.action for c in out}

        acceptish = any(
            k in action
            for k in (
                "accept",
                "agree to",
                "take the deal",
                "take the bargain",
                "i'll help",
                "i will help",
                "offer a sacrifice",
            )
        )
        questish = any(
            k in action for k in ("quest", "trade", "bargain", "mission", "deal", "sacrifice")
        )
        if acceptish and questish and "start_quest" not in actions_set:
            title = "Mira's Bargain" if "mira" in action else "Accepted Charge"
            out.append(
                StateChange(
                    action="start_quest",
                    params={
                        "title": title,
                        "description": f"Accepted: {request.action.strip()[:240]}",
                        "objectives": [
                            "Honor the accepted bargain",
                            "Pursue the lead you were given",
                        ],
                        "reward_xp": 75,
                    },
                )
            )
            actions_set.add("start_quest")

        any_fail = any(getattr(d, "success", None) is False for d in (dice_results or []))
        hostile = any(
            w in action
            for w in (
                "attack",
                "fight",
                "strike",
                "combat",
                "creature",
                "beast",
                "defend",
                "parry",
                "dodge",
                "flee",
                "retreat",
                "distract",
                "grapple",
            )
        )
        if (
            any_fail
            and "apply_damage" not in actions_set
            and "damage_combatant" not in actions_set
            and (state.combat is not None or hostile)
        ):
            out.append(
                StateChange(
                    action="apply_damage",
                    params={"amount": 2 if state.combat else 1},
                )
            )
        return out

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
        # Do not invent people from dialogue alone when the scene is empty.
        if not state.nearby_npcs:
            return []
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
