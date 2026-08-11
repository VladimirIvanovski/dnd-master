from app.database.models import Campaign, Character, User, Location
from app.database.repositories.campaign import CampaignRepository, UserRepository
from app.database.repositories.character import CharacterRepository, InventoryRepository
from app.database.repositories.event import EventRepository
from app.database.repositories.world import QuestRepository
from app.game.engine import GameEngine
from app.game.state import GameStateLoader
from app.schemas.gameplay import StateChange
from app.services.embedding import EmbeddingService
from app.services.memory import MemoryService
from app.utils.ids import utcnow
import uuid


def _seed(db):
    user = User(id=uuid.uuid4(), username="t", display_name="T", created_at=utcnow())
    db.add(user)
    db.flush()
    campaign = Campaign(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Test",
        description="",
        world_state={},
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(campaign)
    db.flush()
    loc = Location(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        name="Town",
        description="A town",
        created_at=utcnow(),
    )
    db.add(loc)
    db.flush()
    character = Character(
        id=uuid.uuid4(),
        user_id=user.id,
        campaign_id=campaign.id,
        location_id=loc.id,
        name="Hero",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(character)
    db.flush()
    return user, campaign, loc, character


def test_repositories_and_models(db):
    user, campaign, loc, character = _seed(db)
    assert CampaignRepository(db).get(campaign.id).name == "Test"
    assert CharacterRepository(db).get(character.id).name == "Hero"
    inv = InventoryRepository(db)
    inv.add_item(character.id, campaign.id, "Sword", quantity=1)
    assert len(inv.list_for_character(character.id)) == 1


def test_game_state_loader(db):
    _, campaign, _, character = _seed(db)
    state = GameStateLoader(db).load(campaign.id, character.id)
    assert state.character.name == "Hero"
    assert state.current_location is not None
    assert state.current_location.name == "Town"


def test_inventory_and_xp(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.add_item(character.id, campaign.id, "Potion")
    engine.apply_damage(character.id, 3)
    assert CharacterRepository(db).get(character.id).hp == 7
    engine.heal(character.id, 2)
    assert CharacterRepository(db).get(character.id).hp == 9
    xp, level = engine.gain_xp(character.id, 300)
    assert xp >= 300
    assert level >= 2


def test_quests(db):
    _, campaign, _, character = _seed(db)
    engine = GameEngine(db)
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[
            StateChange(
                action="start_quest",
                params={"title": "Rats", "objectives": ["Kill rats"], "reward_xp": 50},
            )
        ],
    )
    quests = QuestRepository(db).active_for_campaign(campaign.id, character.id)
    assert len(quests) == 1
    qid = quests[0].id
    engine.apply_state_changes(
        campaign_id=campaign.id,
        character_id=character.id,
        changes=[StateChange(action="complete_quest", params={"quest_id": str(qid)})],
    )
    assert QuestRepository(db).get(qid).status == "completed"


def test_events_immutable_create(db):
    _, campaign, loc, character = _seed(db)
    repo = EventRepository(db)
    ev = repo.create(
        campaign.id,
        "PLAYER_ENTERED_LOCATION",
        "Entered town",
        character_id=character.id,
        location_id=loc.id,
    )
    recent = repo.recent(campaign.id, limit=5)
    assert recent[0].id == ev.id
    assert recent[0].event_type == "PLAYER_ENTERED_LOCATION"


def test_memory_store_and_retrieve(db):
    _, campaign, loc, character = _seed(db)
    service = MemoryService(db, EmbeddingService(dimensions=1536))
    service.store_candidate(
        campaign.id,
        "The hero met Old Marta at the inn.",
        importance=7,
        location_id=loc.id,
        entity_ids=[str(character.id)],
    )
    # duplicate should be ignored
    assert (
        service.store_candidate(
            campaign.id,
            "The hero met Old Marta at the inn.",
            importance=7,
        )
        is None
    )
    state = GameStateLoader(db).load(campaign.id, character.id)
    memories = service.retrieve(state, "talk to Marta")
    assert any("Marta" in m for m in memories)
