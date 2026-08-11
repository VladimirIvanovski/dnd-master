from __future__ import annotations

import hashlib
import math

from app.core.config import get_settings


class EmbeddingService:
    """Deterministic local embeddings for mock mode; replaceable later."""

    def __init__(self, dimensions: int | None = None):
        self.dimensions = dimensions or get_settings().embedding_dimensions

    def embed(self, text: str) -> list[float]:
        # Pseudo-embedding: stable hash-derived unit vector for offline use.
        digest = hashlib.sha256(text.strip().lower().encode()).digest()
        values: list[float] = []
        seed = digest
        while len(values) < self.dimensions:
            seed = hashlib.sha256(seed).digest()
            for b in seed:
                values.append((b / 255.0) * 2 - 1)
                if len(values) >= self.dimensions:
                    break
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
