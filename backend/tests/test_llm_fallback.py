from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import BaseModel, Field

from app.ai.fallback_provider import (
    USER_LIMIT_MESSAGE,
    FallbackLLMProvider,
    LLMUnavailableError,
    _is_failover_error,
)


class _Tiny(BaseModel):
    narration: str = Field(default="ok")


def _http_error(code: int) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://example.test/v1/chat/completions")
    resp = httpx.Response(code, request=req)
    return httpx.HTTPStatusError("rate limited", request=req, response=resp)


def test_is_failover_detects_429_and_404():
    assert _is_failover_error(_http_error(429))
    assert _is_failover_error(_http_error(402))
    assert _is_failover_error(_http_error(404))
    assert _is_failover_error(_http_error(503))
    assert not _is_failover_error(_http_error(400))


def test_fallback_skips_404_and_uses_next():
    primary = MagicMock()
    primary.generate_structured.side_effect = _http_error(404)
    backup = MagicMock()
    backup.generate_structured.return_value = _Tiny(narration="from backup")

    llm = FallbackLLMProvider([("cerebras:120b", primary), ("groq:120b", backup)])
    out = llm.generate_structured("hi", _Tiny, system="sys")
    assert out.narration == "from backup"
    primary.generate_structured.assert_called_once()
    backup.generate_structured.assert_called_once()


def test_fallback_raises_friendly_when_all_fail():
    a = MagicMock()
    a.generate.side_effect = _http_error(429)
    b = MagicMock()
    b.generate.side_effect = _http_error(404)
    llm = FallbackLLMProvider([("a", a), ("b", b)])
    with pytest.raises(LLMUnavailableError, match="Cerebras and Groq") as ei:
        llm.generate("hi")
    assert str(ei.value) == USER_LIMIT_MESSAGE
