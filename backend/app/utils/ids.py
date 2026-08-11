import uuid
from datetime import datetime, timezone


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
