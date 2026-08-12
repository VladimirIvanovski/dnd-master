from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings


class AssetStorageService:
    def __init__(self, root: Path | None = None):
        settings = get_settings()
        self.root = root or Path(settings.asset_storage_path)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, storage_key: str, data: bytes) -> Path:
        path = self.root / storage_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def exists(self, storage_key: str) -> bool:
        return (self.root / storage_key).is_file()

    def read(self, storage_key: str) -> bytes:
        return (self.root / storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self.root / storage_key
        if path.is_file():
            path.unlink()

    def absolute_path(self, storage_key: str) -> Path:
        return self.root / storage_key
