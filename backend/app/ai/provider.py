from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Replaceable LLM interface. Game logic must not depend on a concrete model."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        raise NotImplementedError

    @abstractmethod
    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        raise NotImplementedError

    async def astream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        for chunk in self.stream(prompt, system=system):
            yield chunk
