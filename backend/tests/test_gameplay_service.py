from app.ai.dm_service import DMService
from app.ai.mock_provider import MockLLMProvider
from app.game.state import GameStateLoader
from app.schemas.gameplay import DMResponse, PlayerActionRequest, StateChange
from app.services.gameplay import GameplayService
from app.game.engine import GameEngine
from tests.conftest import start_campaign


def test_gameplay_service_with_mock_llm(db):
    _user, campaign, character = start_campaign(db, username="aria_owner")
    # rename for test clarity — character already named Hero; recreate path uses fixed helper
    character.name = "Aria"
    db.commit()

    fixed = DMResponse(
        narration="Marta nods and hands you a rusty key.",
        dialogue=[{"speaker": "Marta", "text": "Keep this safe."}],
        events=[
            {
                "event_type": "ITEM_ACQUIRED",
                "summary": "Received a rusty key",
                "importance": 6,
            }
        ],
        state_changes=[
            StateChange(action="add_item", params={"name": "Rusty Key", "quantity": 1}),
            StateChange(action="gain_xp", params={"amount": 10}),
        ],
        memory_candidates=[
            {"content": "Marta gave Aria a rusty key.", "importance": 6}
        ],
    )
    service = GameplayService(
        db,
        dm=DMService(MockLLMProvider(fixed_response=fixed)),
        engine=GameEngine(db),
    )
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="Ask Marta for help",
        )
    )
    assert "rusty key" in result.narration.lower() or "Marta" in result.narration
    assert any("added item" in c for c in result.applied_changes)
    assert result.applied_events
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert any(i.name == "Rusty Key" for i in state.inventory)


def test_rejects_illegal_state_change(db):
    _user, campaign, character = start_campaign(db, username="borin_owner")
    engine = GameEngine(db)
    result = engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="drop_table", params={})],
    )
    assert result.rejected
    assert not result.applied


def test_sanitize_dialogue_requires_living_nearby():
    from uuid import uuid4

    from app.schemas.gameplay import DialogueLine
    from app.schemas.state import CharacterState, GameState, NPCState

    ch = CharacterState(
        id=uuid4(),
        name="Hero",
        race="Human",
        class_name="Fighter",
        level=1,
        xp=0,
        hp=10,
        max_hp=10,
        ac=12,
        gold=0,
        abilities={},
    )
    ghost = DialogueLine(speaker="Ghost", text="Boo")
    empty = GameState(campaign_id=uuid4(), campaign_name="T", character=ch, nearby_npcs=[])
    assert GameplayService._sanitize_dialogue(empty, [ghost]) == []
    present = GameState(
        campaign_id=uuid4(),
        campaign_name="T",
        character=ch,
        nearby_npcs=[NPCState(id=uuid4(), name="Marta", title="chandler")],
    )
    kept = GameplayService._sanitize_dialogue(
        present, [ghost, DialogueLine(speaker="Marta", text="Hello")]
    )
    assert [d.speaker for d in kept] == ["Marta"]


def test_talk_refused_when_nobody_is_nearby(db):
    from tests.test_game_core import _seed

    _, campaign, _, character = _seed(db)
    service = GameplayService(db)
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="Talk to the bartender",
        )
    )
    assert result.dialogue == []
    assert "no one" in result.narration.lower()


def test_use_missing_knife_is_refused_without_dm(db):
    from tests.test_game_core import _seed

    _, campaign, _, character = _seed(db)
    service = GameplayService(db)
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="I draw a knife and throw it",
        )
    )
    assert "don't have" in result.narration.lower()
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert not any("knife" in i.name.lower() for i in state.inventory)


def test_legendary_sword_from_dm_is_rejected(db):
    _user, campaign, character = start_campaign(db, username="loot_owner")
    service = GameplayService(db)
    result = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="Give me a legendary sword",
        )
    )
    assert any("cannot conjure" in r for r in result.rejected_changes)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert not any(i.name == "Legendary Sword" for i in state.inventory)


def test_topic_and_rumor_buttons_apply_engine_actions(db):
    from app.database.repositories.world import NPCRepository
    from tests.test_game_core import _seed

    _, campaign, loc, character = _seed(db)
    campaign.world_state = {
        **(campaign.world_state or {}),
        "rumors": [{"id": "well", "text": "The well soured.", "heard": False}],
    }
    db.flush()
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="spawn_npc",
                params={
                    "name": "Wellkeeper",
                    "personality": "quiet",
                    "knowledge": [{"id": "well", "label": "the well", "text": "It ran dry."}],
                },
            )
        ],
    )
    npc = NPCRepository(db).nearby(loc.id)[0]
    service = GameplayService(db, engine=engine)
    asked = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action=f"sys:ask:{npc.id}:well",
        )
    )
    assert asked.applied_changes
    heard = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="sys:hear:well",
        )
    )
    assert heard.applied_changes
    after = GameStateLoader(db).load(campaign.id, character.id)
    assert "well" in after.heard_rumors or any("soured" in r.lower() for r in after.heard_rumors)
    assert "well" not in after.unheard_rumor_ids
    assert "well" in after.nearby_npcs[0].asked


def test_combat_commands_move_and_end_turn(db):
    from tests.test_game_core import _seed

    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_combat",
                params={
                    "combatants": [
                        {
                            "name": "Wolf",
                            "combatant_type": "enemy",
                            "hp": 6,
                            "initiative": 1,
                            "x": 3,
                            "y": 3,
                        },
                        {
                            "name": "Hero",
                            "combatant_type": "player",
                            "hp": 10,
                            "initiative": 20,
                            "ref_id": str(character.id),
                            "x": 3,
                            "y": 1,
                        },
                    ]
                },
            )
        ],
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.combat.whose_turn == "Hero"
    service = GameplayService(db, engine=engine)
    moved = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="sys:move:0:1",
        )
    )
    assert moved.applied_changes
    after = GameStateLoader(db).load(campaign.id, character.id)
    hero = next(c for c in after.combat.combatants if c.name == "Hero")
    assert hero.y == 2
    ended = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="sys:advance",
        )
    )
    assert ended.applied_changes


def test_sys_save_and_load_checkpoint(db):
    from tests.test_game_core import _seed

    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_damage(character.id, 4)
    service = GameplayService(db, engine=engine)
    saved = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="sys:save:camp",
        )
    )
    assert saved.applied_changes
    engine.heal(character.id, 99)
    loaded = service.handle_action(
        PlayerActionRequest(
            campaign_id=campaign.id,
            character_id=character.id,
            action="sys:load:camp",
        )
    )
    assert loaded.applied_changes
    assert engine.characters.get(character.id).hp == 6
