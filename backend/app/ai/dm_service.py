from __future__ import annotations

import logging

from pydantic import ValidationError

from app.ai.context_builder import ContextBuilder
from app.ai.provider import LLMProvider
from app.schemas.gameplay import DMResponse
from app.schemas.state import GameState

logger = logging.getLogger(__name__)


class DMService:
    def __init__(self, llm: LLMProvider, context_builder: ContextBuilder | None = None):
        self.llm = llm
        self.context_builder = context_builder or ContextBuilder()

    def narrate(
        self,
        *,
        state: GameState,
        player_action: str,
        recent_events: list[str],
        memories: list[str],
        recent_conversation: list[str] | None = None,
    ) -> DMResponse:
        system, prompt = self.context_builder.build(
            state=state,
            player_action=player_action,
            recent_events=recent_events,
            memories=memories,
            recent_conversation=recent_conversation,
        )
        try:
            response = self.llm.generate_structured(prompt, DMResponse, system=system)
            return DMResponse.model_validate(response.model_dump())
        except ValidationError as exc:
            logger.warning("Invalid DM output, using safe fallback: %s", exc)
            return DMResponse(
                narration="The world holds still for a moment as fate recalculates.",
                events=[],
                state_changes=[],
            )
