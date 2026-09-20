from __future__ import annotations

import re

_DICE_PROSE = re.compile(
    r"(?i)\b("
    r"you rolled a \d+"
    r"|rolled a \d+"
    r"|natural (?:20|1|twenty|one)"
    r"|\d+d\d+(?:[+-]\d+)?"
    r"|dc\s*\d+"
    r")\b"
)


def scrub_dice_prose(text: str) -> str:
    out = _DICE_PROSE.sub("", text or "")
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def quality_violations(text: str, *, secrets: list[str] | None = None) -> list[str]:
    blob = text or ""
    hits: list[str] = []
    if _DICE_PROSE.search(blob):
        hits.append("dice-in-prose")
    for secret in secrets or []:
        token = str(secret).strip()
        if token and token in blob:
            hits.append("secret-leak")
            break
    return hits
