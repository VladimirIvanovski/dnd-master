from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.provider import LLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

USER_LIMIT_MESSAGE = (
    "Cerebras and Groq are both unavailable right now "
    "(rate limit, outage, or model not found). Please try again in a moment."
)


class LLMUnavailableError(RuntimeError):
    """Raised when every provider in the failover chain failed."""

    def __init__(self, detail: str = USER_LIMIT_MESSAGE, *, errors: list[str] | None = None):
        super().__init__(detail)
        self.errors = errors or []


def _is_failover_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        # 404 = model/route missing on that host — try the next provider
        return exc.response.status_code in {404, 408, 429, 500, 502, 503, 504}
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, ValidationError):
        return True
    msg = str(exc).lower()
    return any(
        needle in msg
        for needle in (
            "429",
            "404",
            "too many requests",
            "rate limit",
            "not found",
            "timeout",
            "unavailable",
        )
    )


class FallbackLLMProvider(LLMProvider):
    """Try providers in order; on rate-limit / outage / missing model, move to the next."""

    def __init__(self, providers: list[tuple[str, LLMProvider]]):
        if not providers:
            raise ValueError("At least one LLM provider is required")
        self.providers = providers

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return self._run(lambda p: p.generate(prompt, system=system))

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        return self._run(lambda p: p.generate_structured(prompt, schema, system=system))

    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        errors: list[str] = []
        for label, provider in self.providers:
            try:
                logger.info("LLM stream via %s", label)
                yield from provider.stream(prompt, system=system)
                return
            except Exception as exc:  # noqa: BLE001
                if not _is_failover_error(exc):
                    raise
                logger.warning("LLM stream %s failed (%s); trying next", label, exc)
                errors.append(f"{label}: {exc}")
        raise LLMUnavailableError(errors=errors)

    def _run(self, fn):
        errors: list[str] = []
        for label, provider in self.providers:
            try:
                logger.info("LLM attempt via %s", label)
                return fn(provider)
            except Exception as exc:  # noqa: BLE001
                if not _is_failover_error(exc):
                    raise
                logger.warning("LLM %s failed (%s); trying next fallback", label, exc)
                errors.append(f"{label}: {exc}")
        raise LLMUnavailableError(errors=errors)
