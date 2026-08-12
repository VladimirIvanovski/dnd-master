from app.services.dialogue_dedupe import strip_embedded_dialogue
from app.schemas.gameplay import DialogueLine


def test_strip_embedded_dialogue_removes_quoted_speech():
    narration = (
        "Talira nods, eyes narrowing. "
        "'If you think you can get close to that light, be careful.' "
        "She hands you a charm."
    )
    dialogue = [
        DialogueLine(
            speaker="Talira",
            text="If you think you can get close to that light, be careful.",
        )
    ]
    out = strip_embedded_dialogue(narration, dialogue)
    assert "If you think you can get close" not in out
    assert "Talira nods" in out
    assert "charm" in out


def test_strip_split_dialogue_inside_one_quote():
    narration = (
        "Talira nods, eyes narrowing. "
        "'If you think you can get close to that light, be careful. "
        "The dunes are unforgiving. "
        "Bring back any clue you find.' "
        "She hands you a small brass token."
    )
    dialogue = [
        DialogueLine(
            speaker="Talira Vexthorn",
            text="If you think you can get close to that light, be careful. The dunes are unforgiving.",
        ),
        DialogueLine(
            speaker="Talira Vexthorn",
            text="Bring back any clue you find.",
        ),
    ]
    out = strip_embedded_dialogue(narration, dialogue)
    assert "If you think" not in out
    assert "Bring back" not in out
    assert "Talira nods" in out
    assert "brass token" in out
