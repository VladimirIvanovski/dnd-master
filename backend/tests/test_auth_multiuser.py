"""Auth, isolation, WebSocket, and concurrent multi-user tests."""

from concurrent.futures import ThreadPoolExecutor, as_completed


def test_register_login_me(client):
    reg = client.post(
        "/api/auth/register",
        json={"username": "reg_user", "password": "password123", "display_name": "Reg"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "reg_user"

    login = client.post(
        "/api/auth/login",
        json={"username": "reg_user", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    bad = client.post(
        "/api/auth/login",
        json={"username": "reg_user", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_cross_user_isolation(client, auth_client):
    headers_a, _ = auth_client("alice_iso")
    headers_b, _ = auth_client("bob_iso")

    camp_a = client.post(
        "/api/campaigns",
        json={"name": "Alice World", "description": "secret"},
        headers=headers_a,
    ).json()
    char_a = client.post(
        "/api/characters",
        json={"campaign_id": camp_a["id"], "name": "Aria"},
        headers=headers_a,
    ).json()

    assert client.get(f"/api/campaigns/{camp_a['id']}", headers=headers_b).status_code == 403
    assert client.get(f"/api/characters/{char_a['id']}", headers=headers_b).status_code == 403
    assert client.get(f"/api/inventory/{char_a['id']}", headers=headers_b).status_code == 403
    assert (
        client.get(
            f"/api/quests?campaign_id={camp_a['id']}",
            headers=headers_b,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/gameplay/action",
            json={
                "campaign_id": camp_a["id"],
                "character_id": char_a["id"],
                "action": "Steal the plot",
            },
            headers=headers_b,
        ).status_code
        == 403
    )

    list_b = client.get("/api/campaigns", headers=headers_b).json()
    assert all(c["id"] != camp_a["id"] for c in list_b)

    list_a = client.get("/api/campaigns", headers=headers_a).json()
    assert any(c["id"] == camp_a["id"] for c in list_a)


def test_ws_requires_token(client, auth_client):
    headers_a, _ = auth_client("ws_owner")
    headers_b, _ = auth_client("ws_intruder")
    camp = client.post(
        "/api/campaigns",
        json={"name": "WS Camp", "description": ""},
        headers=headers_a,
    ).json()
    char = client.post(
        "/api/characters",
        json={"campaign_id": camp["id"], "name": "Hero"},
        headers=headers_a,
    ).json()

    rejected = False
    try:
        with client.websocket_connect("/ws/gameplay"):
            pass
    except Exception:
        rejected = True
    assert rejected

    token_a = headers_a["Authorization"].split(" ", 1)[1]
    token_b = headers_b["Authorization"].split(" ", 1)[1]

    with client.websocket_connect(f"/ws/gameplay?token={token_b}") as ws:
        ws.send_json(
            {
                "campaign_id": camp["id"],
                "character_id": char["id"],
                "action": "Intrude",
            }
        )
        msg = ws.receive_json()
        if msg.get("type") == "status":
            msg = ws.receive_json()
        assert msg.get("type") == "error"

    with client.websocket_connect(f"/ws/gameplay?token={token_a}") as ws:
        ws.send_json(
            {
                "campaign_id": camp["id"],
                "character_id": char["id"],
                "action": "Look around",
            }
        )
        msg = ws.receive_json()
        while msg.get("type") != "result":
            assert msg.get("type") != "error", msg
            msg = ws.receive_json()
        assert msg["data"]["narration"]


def _play(client, headers, name: str) -> str:
    camp = client.post(
        "/api/campaigns",
        json={"name": name, "description": f"world for {name}"},
        headers=headers,
    )
    assert camp.status_code == 200, camp.text
    campaign = camp.json()
    ch = client.post(
        "/api/characters",
        json={"campaign_id": campaign["id"], "name": f"Hero-{name}"},
        headers=headers,
    )
    assert ch.status_code == 200, ch.text
    character = ch.json()
    action = client.post(
        "/api/gameplay/action",
        json={
            "campaign_id": campaign["id"],
            "character_id": character["id"],
            "action": "Survey the surroundings",
        },
        headers=headers,
    )
    assert action.status_code == 200, action.text
    return campaign["id"]


def test_concurrent_independent_campaigns(client, auth_client):
    headers_a, _ = auth_client("conc_a")
    headers_b, _ = auth_client("conc_b")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_play, client, headers_a, "Alpha"),
            pool.submit(_play, client, headers_b, "Beta"),
        ]
        camp_ids = [f.result() for f in as_completed(futures)]

    assert len(set(camp_ids)) == 2
    ids_a = {c["id"] for c in client.get("/api/campaigns", headers=headers_a).json()}
    ids_b = {c["id"] for c in client.get("/api/campaigns", headers=headers_b).json()}
    assert ids_a.isdisjoint(ids_b)
    assert camp_ids[0] in ids_a or camp_ids[0] in ids_b
    assert camp_ids[1] in ids_a or camp_ids[1] in ids_b
    assert len(ids_a) >= 1
    assert len(ids_b) >= 1
