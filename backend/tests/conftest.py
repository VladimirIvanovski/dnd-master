import os

# Disable rate limiting noise in tests.
os.environ["LLM_PROVIDER"] = "mock"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ["IMAGE_GENERATION_ENABLED"] = "true"
os.environ["IMAGE_MODEL"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.database.models  # noqa: F401
from app.core.config import get_settings
from app.database.base import Base
from app.database.repositories import UserRepository
from app.database.session import get_db
from app.main import app as fastapi_app
from app.schemas.common import CampaignCreate, CharacterCreate
from app.services.auth import create_access_token, hash_password
from app.services.campaign import CampaignService, CharacterService
from app.core.rate_limit import limiter

get_settings.cache_clear()
limiter.enabled = False


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    eng = create_engine(settings.database_url, pool_pre_ping=True)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    yield eng


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


def make_user(db, username: str = "player", password: str = "password123"):
    user = UserRepository(db).create(
        username=username,
        password_hash=hash_password(password),
        display_name=username,
    )
    db.commit()
    db.refresh(user)
    return user


def auth_header(user) -> dict[str, str]:
    token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def start_campaign(db, username: str = "player"):
    user = make_user(db, username=username)
    campaign = CampaignService(db).create(
        CampaignCreate(name="Persist", description="t"),
        owner_id=user.id,
    )
    character = CharacterService(db).create(
        CharacterCreate(campaign_id=campaign.id, name="Hero"),
        user_id=user.id,
    )
    return user, campaign, character


@pytest.fixture()
def auth_client(client, db):
    """Register via API and return (client, headers, user_body)."""

    def _register(username: str = "alice", password: str = "password123"):
        resp = client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        return headers, body["user"]

    return _register
