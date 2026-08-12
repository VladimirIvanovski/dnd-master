import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Campaign, User


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: uuid.UUID, name: str, description: str = "") -> Campaign:
        campaign = Campaign(owner_id=owner_id, name=name, description=description, world_state={})
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def get(self, campaign_id: uuid.UUID) -> Campaign | None:
        return self.db.get(Campaign, campaign_id)

    def list_for_user(self, owner_id: uuid.UUID) -> list[Campaign]:
        return list(
            self.db.scalars(select(Campaign).where(Campaign.owner_id == owner_id)).all()
        )


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def create(self, username: str, password_hash: str, display_name: str | None = None) -> User:
        user = User(
            username=username,
            display_name=display_name or username,
            password_hash=password_hash,
        )
        self.db.add(user)
        self.db.flush()
        return user
