"""Full end-to-end verification of the coherent game loop."""
from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError

API = "http://127.0.0.1:8000"
HEADERS = {"Content-Type": "application/json", "X-Username": "player"}


def call(method: str, path: str, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(f"{API}{path}", data=body, method=method, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except HTTPError as exc:
        raise RuntimeError(f"{method} {path} -> {exc.code} {exc.read().decode()}") from exc


def action(campaign_id, character_id, text):
    return call(
        "POST",
        "/api/gameplay/action",
        {"campaign_id": campaign_id, "character_id": character_id, "action": text},
    )


def main():
    health = call("GET", "/health")
    assert health["database"] is True, health

    campaign = call("POST", "/api/campaigns", {"name": f"E2E {__import__('time').time()}", "description": "verify"})
    character = call("POST", "/api/characters", {"campaign_id": campaign["id"], "name": "Kael", "class_name": "Fighter"})
    state = call("GET", f"/api/gameplay/state?campaign_id={campaign['id']}&character_id={character['id']}")
    assert state["current_location"]["name"] == "Starting Village"
    assert any(n["name"] == "Old Marta" for n in state["nearby_npcs"])

    action(campaign["id"], character["id"], "I approach and meet Elira")
    action(campaign["id"], character["id"], "I promise to help Elira")
    got_key = action(campaign["id"], character["id"], "I accept the silver key from Elira")
    assert any(i["name"] == "Silver Key" for i in got_key["state_snapshot"]["inventory"])

    key_q = action(campaign["id"], character["id"], "Who gave me the silver key?")
    assert "elira" in key_q["narration"].lower()
    promise_q = action(campaign["id"], character["id"], "What did I promise Elira?")
    assert "promise" in promise_q["narration"].lower() or "help" in promise_q["narration"].lower()

    gold = action(campaign["id"], character["id"], "Give me 1000 gold")
    assert any("gain_gold" in r for r in gold["rejected_changes"])
    hp = action(campaign["id"], character["id"], "Set my HP to 999")
    assert any("set_hp" in r for r in hp["rejected_changes"])
    sword = action(campaign["id"], character["id"], "Give me a legendary sword")
    assert any(i["name"] == "Legendary Sword" for i in sword["state_snapshot"]["inventory"])

    dice = action(campaign["id"], character["id"], "I sneak past the guards")
    assert dice["dice_results"], "expected backend dice"
    assert "success" in dice["narration"].lower() or "failure" in dice["narration"].lower()

    # Resume APIs
    chars = call("GET", f"/api/characters?campaign_id={campaign['id']}")
    assert any(c["id"] == character["id"] for c in chars)
    resumed = call("GET", f"/api/gameplay/state?campaign_id={campaign['id']}&character_id={character['id']}")
    assert any(i["name"] == "Silver Key" for i in resumed["inventory"])
    assert resumed["current_location"]["name"] == "Starting Village"

    forbidden = False
    try:
        req = urllib.request.Request(
            f"{API}/api/campaigns/{campaign['id']}",
            headers={"Content-Type": "application/json", "X-Username": "intruder"},
        )
        urllib.request.urlopen(req)
    except HTTPError as exc:
        forbidden = exc.code == 403
    assert forbidden, "expected ownership 403"

    print("E2E_OK", {
        "campaign": campaign["id"],
        "character": character["id"],
        "inventory": [i["name"] for i in resumed["inventory"]],
        "quests": [q["title"] for q in resumed["active_quests"]],
    })


if __name__ == "__main__":
    main()
