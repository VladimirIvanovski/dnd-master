from __future__ import annotations

import logging

from app.ai.fallback_provider import FallbackLLMProvider
from app.ai.groq_provider import GroqProvider
from app.ai.mock_provider import MockLLMProvider
from app.ai.provider import LLMProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "mock":
        return MockLLMProvider()

    if provider == "cerebras":
        chain = _cerebras_failover_chain(settings)
        if len(chain) == 1:
            return chain[0][1]
        labels = " -> ".join(label for label, _ in chain)
        logger.info("LLM failover chain: %s", labels)
        return FallbackLLMProvider(chain)

    if provider == "groq":
        chain = _groq_failover_chain(settings)
        if len(chain) == 1:
            return chain[0][1]
        labels = " -> ".join(label for label, _ in chain)
        logger.info("LLM failover chain: %s", labels)
        return FallbackLLMProvider(chain)

    return MockLLMProvider()


def _append_groq(
    chain: list[tuple[str, LLMProvider]],
    settings,
    model: str | None,
) -> None:
    if not settings.groq_api_key or not model:
        return
    label = f"groq:{model}"
    if any(existing == label for existing, _ in chain):
        return
    chain.append(
        (
            label,
            GroqProvider(
                api_key=settings.groq_api_key,
                model=model,
                base_url=settings.groq_base_url,
                timeout=90.0,
            ),
        )
    )


def _append_cerebras(
    chain: list[tuple[str, LLMProvider]],
    settings,
    model: str | None,
) -> None:
    if not settings.cerebras_api_key or not model:
        return
    label = f"cerebras:{model}"
    if any(existing == label for existing, _ in chain):
        return
    chain.append(
        (
            label,
            GroqProvider(
                api_key=settings.cerebras_api_key,
                model=model,
                base_url=settings.cerebras_base_url,
                timeout=120.0,
            ),
        )
    )


def _groq_extra_fallbacks(settings) -> list[str]:
    """Groq models after OSS: Llama 70B, then Qwen 27B."""
    return [
        settings.groq_fallback_model_2,
        settings.groq_fallback_model_3,
    ]


def _cerebras_failover_chain(settings) -> list[tuple[str, LLMProvider]]:
    """Cerebras 120B → Groq 120B → Cerebras 20B → Groq 20B → Llama 70B → Qwen 27B."""
    chain: list[tuple[str, LLMProvider]] = []
    _append_cerebras(chain, settings, settings.cerebras_model)
    _append_groq(chain, settings, settings.groq_model)
    _append_cerebras(chain, settings, settings.cerebras_fallback_model)
    _append_groq(chain, settings, settings.groq_fallback_model)
    for model in _groq_extra_fallbacks(settings):
        _append_groq(chain, settings, model)

    if not chain:
        raise ValueError(
            "No LLM API keys configured. Set CEREBRAS_API_KEY and/or GROQ_API_KEY, "
            "or use LLM_PROVIDER=mock."
        )
    return chain


def _groq_failover_chain(settings) -> list[tuple[str, LLMProvider]]:
    chain: list[tuple[str, LLMProvider]] = []
    _append_groq(chain, settings, settings.groq_model)
    _append_groq(chain, settings, settings.groq_fallback_model)
    for model in _groq_extra_fallbacks(settings):
        _append_groq(chain, settings, model)
    _append_cerebras(chain, settings, settings.cerebras_model)
    if not chain:
        raise ValueError(
            "GROQ_API_KEY is required when LLM_PROVIDER=groq (or set CEREBRAS_API_KEY)."
        )
    return chain
