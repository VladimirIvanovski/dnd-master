from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.provider import LLMProvider
from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class GroqProvider(LLMProvider):
    """Groq OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("API key is required for this LLM provider")

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return self._chat(prompt, system=system, json_mode=False)

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
    ) -> T:
        schema_hint = json.dumps(schema.model_json_schema(), indent=2)
        structured_system = (
            (system or "")
            + "\n\nReturn ONLY valid JSON matching this schema. No markdown, no commentary.\n"
            + schema_hint
        )
        raw = self._chat(prompt, system=structured_system, json_mode=True)
        try:
            return schema.model_validate(self._parse_json(raw))
        except (ValidationError, json.JSONDecodeError, ValueError) as first:
            logger.warning("Groq structured parse failed, retrying: %s", first)
            repair = (
                "Your previous reply was invalid JSON. Reply again with ONLY corrected JSON "
                f"for schema {schema.__name__}. Previous output:\n{raw[:2000]}"
            )
            raw2 = self._chat(repair, system=structured_system, json_mode=True)
            return schema.model_validate(self._parse_json(raw2))

    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        messages = self._messages(prompt, system)
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                        delta = payload["choices"][0]["delta"].get("content") or ""
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    def _chat(self, prompt: str, *, system: str | None, json_mode: bool) -> str:
        body: dict = {
            "model": self.model,
            "messages": self._messages(prompt, system),
            "temperature": 0.7,
        }
        # gpt-oss on Cerebras defaults to medium reasoning; keep it light for turn latency.
        if "gpt-oss" in (self.model or "").lower() and "cerebras.ai" in self.base_url:
            body["reasoning_effort"] = "low"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _messages(prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = raw.strip()
        fence = JSON_FENCE.search(text)
        if fence:
            text = fence.group(1).strip()
        return json.loads(text)
