from __future__ import annotations

import logging
import re

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
from app.ai.quality import scrub_dice_prose
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

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


_USE_ITEM = re.compile(
    r"\b(?:use|draw|throw|wield|swing|drink|eat)\b\s+(?:the\s+|a\s+|an\s+|my\s+)?([a-z0-9][a-z0-9' -]{0,40})",
    re.I,
)
_GEAR_HINTS = (
    "knife",
    "sword",
    "blade",
    "bow",
    "axe",
    "dagger",
    "potion",
    "torch",
    "shield",
    "staff",
    "wand",
    "rope",
    "lockpick",
    "hammer",
    "spear",
    "crossbow",
    "arrow",
    "key",
    "flask",
    "legendary",
)


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
        direct = self._try_direct(request, state)
        if direct:
            return direct
        refused = self._immediate_refusal(state, request.action)
        if refused:
            return self._commit_turn(
                request,
                state,
                narration=refused,
                changes=[],
                dialogue=[],
                dice_results=[],
                suggested=["Look around carefully", "Check your belongings", "Wait and listen"],
            )

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

        narration = strip_embedded_dialogue(dm_out.narration, dm_out.dialogue)
        dialogue = self._sanitize_dialogue(state, dm_out.dialogue)
        return self._commit_turn(
            request,
            state,
            narration=narration,
            changes=changes,
            dialogue=dialogue,
            dice_results=dice_results,
            events=dm_out.events,
            memories=dm_out.memory_candidates,
            suggested=dm_out.suggested_actions,
            describe_env=describe_env,
            suggestion=suggestion,
        )

    def _immediate_refusal(self, state: GameState, action: str) -> str | None:
        low = (action or "").strip().lower()
        if not low or low.startswith("sys:"):
            return None
        match = _USE_ITEM.search(low)
        if match:
            noun = match.group(1).strip(" .!?,")
            if any(h in noun for h in _GEAR_HINTS):
                owned = [i.name.lower() for i in state.inventory]
                if not any(noun in name or name in noun for name in owned):
                    return f"You don't have {noun}."
        talkish = any(w in low for w in ("talk", "ask ", "speak", "greet", "tell "))
        if talkish and not state.nearby_npcs:
            return "There is no one here to speak with."
        return None

    def _try_direct(self, request: PlayerActionRequest, state: GameState) -> GameplayResponse | None:
        raw = (request.action or "").strip()
        if not raw.startswith("sys:"):
            return None
        parts = raw[4:].split(":")
        kind = parts[0] if parts else ""
        changes: list[StateChange] = []
        narration = "Nothing happens."
        try:
            if kind == "ask" and len(parts) >= 3:
                changes = [
                    StateChange(
                        action="share_knowledge",
                        params={"npc_id": parts[1], "topic_id": parts[2]},
                    )
                ]
                narration = "They tell you what they know."
            elif kind == "hear" and len(parts) >= 2:
                changes = [StateChange(action="hear_rumor", params={"rumor_id": parts[1]})]
                narration = "You catch the rumor clearly now."
            elif kind == "move" and len(parts) >= 3:
                hero = self._player_combatant(state)
                if not hero:
                    raise ValueError("not in combat")
                changes = [
                    StateChange(
                        action="move_combatant",
                        params={
                            "combatant_id": str(hero.id),
                            "dx": int(parts[1]),
                            "dy": int(parts[2]),
                        },
                    )
                ]
                narration = "You shift your footing."
            elif kind == "strike" and len(parts) >= 2:
                changes = [
                    StateChange(
                        action="damage_combatant",
                        params={"combatant_id": parts[1], "amount": 2},
                    )
                ]
                narration = "You strike."
            elif kind == "advance":
                changes = [StateChange(action="advance_turn", params={})]
                narration = "You hold and let the next combatant act."
            elif kind == "save":
                name = parts[1] if len(parts) > 1 else "camp"
                changes = [StateChange(action="save_checkpoint", params={"name": name})]
                narration = "You mark this moment."
            elif kind == "load":
                name = parts[1] if len(parts) > 1 else "camp"
                changes = [StateChange(action="load_checkpoint", params={"name": name})]
                narration = "You return to a marked moment."
            else:
                return None
        except ValueError:
            return None
        return self._commit_turn(
            request, state, narration=narration, changes=changes, dialogue=[], dice_results=[]
        )

    @staticmethod
    def _player_combatant(state: GameState):
        if not state.combat:
            return None
        return next(
            (
                c
                for c in state.combat.combatants
                if c.combatant_type in {"player", "character"}
            ),
            None,
        )

    def _commit_turn(
        self,
        request: PlayerActionRequest,
        state: GameState,
        *,
        narration: str,
        changes: list[StateChange],
        dialogue: list[DialogueLine],
        dice_results: list,
        events: list | None = None,
        memories: list | None = None,
        suggested: list[str] | None = None,
        describe_env: bool = False,
        suggestion=None,
    ) -> GameplayResponse:
        narration = scrub_dice_prose(narration)
        dialogue = [
            DialogueLine(speaker=line.speaker, text=scrub_dice_prose(line.text))
            for line in dialogue
        ]
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
            proposed=events or [],
        )
        apply_result.event_summaries = event_summaries
        apply_result.dice_results = dice_results

        if suggestion is not None:
            meta = get_narrative_meta(state.world_state)
            fired_id = suggestion.archetype.id if suggestion.fire and suggestion.archetype else None
            fired_cat = (
                suggestion.archetype.category if suggestion.fire and suggestion.archetype else None
            )
            new_meta = next_narrative_meta(
                meta,
                state=state,
                described=describe_env,
                fired_event_id=fired_id,
                fired_category=fired_cat,
            )
            self._persist_narrative_meta(request.campaign_id, new_meta)

        for candidate in memories or []:
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
        if apply_result.rejected and not apply_result.applied:
            narration = apply_result.rejected[0].split(": ", 1)[-1]
            narration = f"That doesn't work: {narration}."
        return GameplayResponse(
            narration=narration.strip(),
            dialogue=dialogue,
            dice_results=dice_results,
            applied_events=event_summaries,
            applied_changes=apply_result.applied,
            rejected_changes=apply_result.rejected,
            state_snapshot=refreshed.model_dump(mode="json"),
            suggested_actions=_normalize_suggestions(
                suggested,
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
    def _sanitize_dialogue(state: GameState, dialogue: list[DialogueLine]) -> list[DialogueLine]:
        nearby = {n.name.lower() for n in state.nearby_npcs if getattr(n, "is_alive", True)}
        if not nearby:
            return []
        out: list[DialogueLine] = []
        for line in dialogue or []:
            speaker = (line.speaker or "").strip()
            if speaker.lower() in nearby:
                out.append(line)
        return out

    @staticmethod
    def _dialogue_npcs_as_changes(
        state: GameState, dialogue: list[DialogueLine]
    ) -> list[StateChange]:
        return []
