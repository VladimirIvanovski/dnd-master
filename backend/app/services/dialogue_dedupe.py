from __future__ import annotations

import re


def strip_embedded_dialogue(narration: str, dialogue: list) -> str:
    """Remove spoken lines that were also placed in the dialogue array."""
    out = narration or ""
    texts: list[str] = []
    for line in dialogue or []:
        text = (
            getattr(line, "text", None)
            or (line.get("text") if isinstance(line, dict) else "")
            or ""
        ).strip()
        if len(text) >= 6:
            texts.append(text)

    # Prefer removing the whole speech block when narration quotes it as one string.
    if len(texts) >= 2:
        joined = " ".join(texts)
        out = _remove_speech(out, joined)
    for text in texts:
        out = _remove_speech(out, text)

    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.])", r"\1", out)
    out = re.sub(r"[“\"‘']\s*[”\"’']", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def _remove_speech(haystack: str, speech: str) -> str:
    escaped = re.escape(speech)
    out = re.sub(rf'[“"]\s*{escaped}\s*[”"]', "", haystack)
    out = re.sub(rf"[‘']\s*{escaped}\s*[’']", "", out)
    # Nested inside a larger quote / plain paste
    out = re.sub(escaped, "", out)
    return out
