from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.repositories import EventRepository, MemoryRepository
from app.schemas.state import GameState
from app.services.embedding import EmbeddingService


@dataclass
class RankedMemory:
    content: str
    score: float
    importance: int


class MemoryService:
    def __init__(
        self,
        db: Session,
        embedding: EmbeddingService | None = None,
        *,
        max_results: int = 6,
    ):
        self.db = db
        self.embedding = embedding or EmbeddingService()
        self.memories = MemoryRepository(db)
        self.events = EventRepository(db)
        self.max_results = max_results

    def short_term(self, campaign_id: uuid.UUID, limit: int = 12) -> list[str]:
        events = self.events.recent(campaign_id, limit=limit)
        return [f"[{e.event_type}] {e.summary}" for e in events]

    def store_candidate(
        self,
        campaign_id: uuid.UUID,
        content: str,
        *,
        importance: int = 5,
        entity_ids: list[str] | None = None,
        location_id: uuid.UUID | None = None,
        quest_ids: list[str] | None = None,
        event_id: uuid.UUID | None = None,
    ):
        if importance < 4:
            return None
        emb = self.embedding.embed(content)
        # Near-duplicate: skip if a very similar memory already exists.
        similar = self.memories.semantic_search(campaign_id, emb, limit=1)
        if similar and similar[0][1] < 0.08 and similar[0][0].importance >= importance - 1:
            return None
        return self.memories.create(
            campaign_id,
            content,
            emb,
            importance=importance,
            entity_ids=entity_ids,
            location_id=location_id,
            quest_ids=quest_ids,
            event_id=event_id,
        )

    def retrieve(self, state: GameState, player_action: str) -> list[str]:
        query = f"{player_action}\n{state.current_location.name if state.current_location else ''}"
        query_emb = self.embedding.embed(query)
        semantic = self.memories.semantic_search(
            state.campaign_id, query_emb, limit=self.max_results * 2
        )
        recent = self.memories.recent(state.campaign_id, limit=max(self.max_results * 2, 12))

        entity_ids = {str(n.id) for n in state.nearby_npcs}
        entity_ids.add(str(state.character.id))
        quest_ids = {str(q.id) for q in state.active_quests}
        location_id = state.current_location.id if state.current_location else None
        tokens = {t for t in player_action.lower().replace("?", " ").split() if len(t) > 2}

        ranked: dict[str, RankedMemory] = {}

        def consider(mem, similarity: float, recency_boost: float) -> None:
            text_l = mem.content.lower()
            keyword_hit = sum(1 for t in tokens if t in text_l)
            score = self._rank(
                similarity=similarity,
                importance=mem.importance,
                recency_boost=recency_boost,
                entity_hit=bool(set(mem.entity_ids or []) & entity_ids),
                location_hit=bool(location_id and mem.location_id == location_id),
                quest_hit=bool(set(mem.quest_ids or []) & quest_ids),
            )
            score += min(0.25, 0.08 * keyword_hit)
            key = str(mem.id)
            if key not in ranked or ranked[key].score < score:
                ranked[key] = RankedMemory(mem.content, score, mem.importance)

        for mem, distance in semantic:
            consider(mem, similarity=1.0 / (1.0 + distance), recency_boost=0.2)

        for i, mem in enumerate(recent):
            recency = 1.0 - (i / max(len(recent), 1))
            consider(mem, similarity=0.25, recency_boost=recency)

        ordered = sorted(ranked.values(), key=lambda m: m.score, reverse=True)
        return [m.content for m in ordered[: self.max_results]]

    @staticmethod
    def _rank(
        *,
        similarity: float,
        importance: int,
        recency_boost: float,
        entity_hit: bool,
        location_hit: bool,
        quest_hit: bool,
    ) -> float:
        return (
            0.40 * similarity
            + 0.20 * (importance / 10.0)
            + 0.15 * recency_boost
            + 0.10 * (1.0 if entity_hit else 0.0)
            + 0.10 * (1.0 if location_hit else 0.0)
            + 0.05 * (1.0 if quest_hit else 0.0)
        )
