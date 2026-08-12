from app.services.gameplay import _normalize_suggestions


def test_normalize_suggestions_pads_and_trims():
    assert _normalize_suggestions(
        ["Ask the smith about the key", "  ", "Sneak out back", "extra"],
        has_nearby_npcs=True,
    ) == [
        "Ask the smith about the key",
        "Sneak out back",
        "extra",
    ]


def test_normalize_suggestions_fallback_three():
    out = _normalize_suggestions([])
    assert len(out) == 3
    assert out[0] == "Look around carefully"
    assert "Talk to someone nearby" not in out


def test_normalize_suggestions_with_npcs_allows_talk():
    out = _normalize_suggestions([], has_nearby_npcs=True)
    assert "Talk to someone nearby" in out


def test_normalize_drops_talk_when_alone():
    out = _normalize_suggestions(
        ["Talk to someone nearby", "Climb the wall", "Wait quietly"],
        has_nearby_npcs=False,
    )
    assert "Talk to someone nearby" not in out
    assert out[0] == "Climb the wall"
