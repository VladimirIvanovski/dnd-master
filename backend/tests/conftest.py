import os

# Force mock LLM in tests so campaign-brief generation stays offline.
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.database.models  # noqa: F401
from app.core.config import get_settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app as fastapi_app

get_settings.cache_clear()


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
