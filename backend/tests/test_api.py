def test_api_campaign_character_gameplay(client, auth_client):
    headers, _ = auth_client("api_user")
    c = client.post(
        "/api/campaigns",
        json={"name": "API Campaign", "description": "test"},
        headers=headers,
    )
    assert c.status_code == 200
    campaign = c.json()
    assert campaign["name"] == "API Campaign"

    ch = client.post(
        "/api/characters",
        json={"campaign_id": campaign["id"], "name": "Lyra", "class_name": "Rogue"},
        headers=headers,
    )
    assert ch.status_code == 200
    character = ch.json()
    assert character["name"] == "Lyra"

    q = client.post(
        "/api/quests",
        json={
            "campaign_id": campaign["id"],
            "character_id": character["id"],
            "title": "Find the map",
            "objectives": ["Ask around town"],
        },
        headers=headers,
    )
    assert q.status_code == 200

    inv = client.get(f"/api/inventory/{character['id']}", headers=headers)
    assert inv.status_code == 200
    assert inv.json() == []

    action = client.post(
        "/api/gameplay/action",
        json={
            "campaign_id": campaign["id"],
            "character_id": character["id"],
            "action": "Look around the village square",
        },
        headers=headers,
    )
    assert action.status_code == 200
    body = action.json()
    assert body["narration"]
    assert "state_snapshot" in body


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] is True


def test_unauthenticated_campaign_rejected(client):
    r = client.post("/api/campaigns", json={"name": "Nope", "description": ""})
    assert r.status_code == 401
