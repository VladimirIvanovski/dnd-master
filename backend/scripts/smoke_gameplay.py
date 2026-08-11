import json
import urllib.request


def call(method, path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


print("HEALTH", call("GET", "/health"))
campaign = call("POST", "/api/campaigns", {"name": "Live Verify", "description": "smoke"})
print("CAMPAIGN", campaign["id"], campaign["name"])
character = call(
    "POST",
    "/api/characters",
    {"campaign_id": campaign["id"], "name": "Kael", "class_name": "Fighter"},
)
print("CHARACTER", character["id"], character["hp"], character["location_id"])
result = call(
    "POST",
    "/api/gameplay/action",
    {
        "campaign_id": campaign["id"],
        "character_id": character["id"],
        "action": "Explore the village and greet Old Marta",
    },
)
print("NARRATION", result["narration"][:120])
print("EVENTS", result["applied_events"])
print("CHANGES", result["applied_changes"], result["rejected_changes"])
print("LOCATION", result["state_snapshot"]["current_location"]["name"])
print("NPCS", [n["name"] for n in result["state_snapshot"]["nearby_npcs"]])
print("OK")
