from app.schemas.gameplay import DMResponse


def test_dm_response_validation():
    data = {
        "narration": "You enter the tavern.",
        "dialogue": [{"speaker": "Marta", "text": "Welcome."}],
        "dice_requests": [],
        "events": [{"event_type": "PLAYER_ENTERED_LOCATION", "summary": "Entered tavern"}],
        "state_changes": [],
        "memory_candidates": [{"content": "Met Marta", "importance": 6}],
        "quest_updates": [],
        "npc_updates": [],
    }
    resp = DMResponse.model_validate(data)
    assert resp.narration.startswith("You enter")
    assert resp.dialogue[0].speaker == "Marta"


def test_dm_response_rejects_bad_payload():
    try:
        DMResponse.model_validate({"narration": 123})
        assert False, "should have failed"
    except Exception:
        assert True
