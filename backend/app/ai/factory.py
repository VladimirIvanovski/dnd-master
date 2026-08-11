from __future__ import annotations

from app.ai.groq_provider import GroqProvider
from app.ai.mock_provider import MockLLMProvider
from app.ai.provider import LLMProvider
from app.core.config import get_settings


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "groq":
        return GroqProvider()
    return MockLLMProvider()
