from app.game.worldkit import (
    add_fact,
    apply_resistance,
    chebyshev,
    disarm_trap,
    distance_ft,
    faction_delta,
    hear_rumor,
    loot_container,
    public_traps,
    record_death_save,
    seed_rumors,
    spot_trap,
    step_toward,
    take_from_stock,
    trigger_trap,
    unlock_container,
)


def test_resistance_halves_and_immunity():
    extra = {"resistances": {"fire": 0.5, "cold": 0.0}}
    assert apply_resistance(10, extra, "fire") == 5
    assert apply_resistance(10, extra, "cold") == 0
    assert apply_resistance(10, extra, "slash") == 10


def test_stock_take_and_out_of_stock():
    extra = {"gold": 0, "stock": [{"name": "Torch", "quantity": 1, "price": 2}]}
    extra, row = take_from_stock(extra, "torch", 1)
    assert row["price"] == 2
    assert extra["gold"] == 2
    assert extra["stock"] == []
    try:
        take_from_stock(extra, "Torch", 1)
        assert False, "expected out of stock"
    except ValueError as exc:
        assert "stock" in str(exc) or "sell" in str(exc)


def test_knowledge_and_death_saves():
    extra = add_fact({}, "the vault key is under the mat")
    extra = add_fact(extra, "the vault key is under the mat")
    assert extra["known_facts"] == ["the vault key is under the mat"]
    extra, outcome = record_death_save({"death_saves": {"fail": 2}}, success=False)
    assert outcome == "dead"
    extra, outcome = record_death_save({}, success=True)
    extra, outcome = record_death_save(extra, success=True)
    extra, outcome = record_death_save(extra, success=True)
    assert outcome == "stable"


def test_container_lock_and_loot():
    extra = {
        "containers": [
            {"id": "chest-1", "name": "Oak chest", "locked": True, "items": [{"name": "Key"}]}
        ]
    }
    try:
        loot_container(extra, "chest-1")
        assert False, "locked"
    except ValueError:
        pass
    extra = unlock_container(extra, "chest-1")
    extra, items = loot_container(extra, "chest-1")
    assert items[0]["name"] == "Key"
    assert extra["containers"][0]["items"] == []


def test_faction_clamped():
    ws = faction_delta({}, "Watch", 40)
    ws = faction_delta(ws, "Watch", 80)
    assert ws["factions"]["Watch"]["player_rep"] == 100


def test_hidden_trap_and_rumor_helpers():
    extra = {"traps": [{"id": "pit-1", "name": "Pit", "armed": True, "damage": 4, "spotted": False}]}
    assert public_traps(extra) == []
    extra = spot_trap(extra, "pit-1")
    assert public_traps(extra)[0]["armed"] is True
    extra = disarm_trap(extra, "pit-1")
    assert extra["traps"][0]["armed"] is False
    extra = {
        "traps": [{"id": "dart-1", "name": "Dart", "armed": True, "damage": 2, "spotted": False}]
    }
    extra, sprung = trigger_trap(extra, "dart-1")
    assert sprung["damage"] == 2
    assert extra["traps"][0]["spotted"] is True
    ws, text = hear_rumor({"rumors": [{"id": "well", "text": "dry well", "heard": False}]}, rumor_id="well")
    assert text == "dry well"
    assert ws["rumors"][0]["heard"] is True


def test_seed_rumors_and_grid_step():
    import random

    ws = seed_rumors({}, place="Graymoor", people=["Marta"], rng=random.Random(2))
    assert len(ws["rumors"]) >= 2
    again = seed_rumors(ws, place="Graymoor", rng=random.Random(2))
    assert len(again["rumors"]) == len(ws["rumors"])
    assert step_toward((3, 6), (3, 1)) == (3, 5)
    assert chebyshev((3, 1), (3, 6)) == 5
    assert distance_ft({"x": 3, "y": 1}, {"x": 3, "y": 6}) == 25


def test_tick_vitals_exhausts():
    from app.game.rules import tick_vitals

    extra = tick_vitals({}, steps=20)
    assert extra["hunger"] >= 80
    assert extra["thirst"] >= 80
    assert extra["stamina"] <= 10
    assert "exhausted" in extra["conditions"]


def test_knowledge_packets_hide_body_and_secrets():
    from app.game.worldkit import packet_text, public_topics, step_away

    knowledge = [
        {"id": "well", "label": "the well", "text": "WELL_POISON_TOKEN in the cistern"},
        "KING_IS_A_LIZARD_TOKEN lives downstairs",
    ]
    topics = public_topics(knowledge, secrets=["KING_IS_A_LIZARD_TOKEN"])
    assert topics == [{"id": "well", "label": "the well"}]
    assert packet_text(knowledge, "well", secrets=["KING_IS_A_LIZARD_TOKEN"]).startswith("WELL_POISON")
    try:
        packet_text(knowledge, "king", secrets=["KING_IS_A_LIZARD_TOKEN"])
        assert False, "secret packet"
    except ValueError:
        pass
    assert step_away((3, 2), (3, 1)) == (3, 3)
