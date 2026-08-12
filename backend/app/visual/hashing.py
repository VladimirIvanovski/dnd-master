from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def normalize_name(name: str) -> str:
    text = name.lower().strip()
    text = re.sub(r"^(the|a|an)\s+", "", text)
    text = re.sub(r"(village|town|city|settlement)\s+of\s+", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def visual_state_hash(state: dict[str, Any]) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def image_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
