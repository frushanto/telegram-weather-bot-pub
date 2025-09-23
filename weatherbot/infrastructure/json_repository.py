import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional

from ..core.exceptions import StorageError
from ..domain.repositories import UserRepository

logger = logging.getLogger(__name__)


class JsonUserRepository(UserRepository):

    def __init__(self, storage_path: str = "storage.json"):
        self.storage_path = Path(storage_path)
        self._lock = asyncio.Lock()
        self._storage: Dict[str, Dict] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:

        if not self._loaded:
            await self._load_storage()

    async def _load_storage(self) -> None:

        async with self._lock:
            if self._loaded:
                return
            try:
                if (
                    not self.storage_path.exists()
                    or self.storage_path.stat().st_size == 0
                ):
                    self._storage = {}
                    self._loaded = True
                    return
                with self.storage_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._storage = data if isinstance(data, dict) else {}
                    self._loaded = True
            except json.JSONDecodeError:
                logger.warning(
                    f"{self.storage_path} empty/corrupted — starting with empty storage."
                )
                self._storage = {}
                self._loaded = True
            except Exception as e:
                logger.exception(f"Failed to read {self.storage_path}")
                raise StorageError(f"Could not load storage: {e}")

    async def _save_storage(self) -> None:

        async with self._lock:
            try:
                tmp_path = self.storage_path.with_suffix(".tmp")
                with tmp_path.open("w", encoding="utf-8") as f:
                    json.dump(self._storage, f, ensure_ascii=False, indent=2)
                tmp_path.replace(self.storage_path)
            except Exception as e:
                logger.exception(f"Failed to save {self.storage_path}")
                raise StorageError(f"Could not save storage: {e}")

    async def get_user_data(self, chat_id: str) -> Optional[Dict]:

        await self._ensure_loaded()
        return self._storage.get(str(chat_id))

    async def save_user_data(self, chat_id: str, data: Dict) -> None:

        await self._ensure_loaded()
        async with self._lock:
            self._storage[str(chat_id)] = data
        await self._save_storage()

    async def delete_user_data(self, chat_id: str) -> bool:

        await self._ensure_loaded()
        async with self._lock:
            removed = self._storage.pop(str(chat_id), None)
        if removed is not None:
            await self._save_storage()
            return True
        return False

    async def get_all_users(self) -> Dict[str, Dict]:

        await self._ensure_loaded()
        return self._storage.copy()

    async def get_user_language(self, chat_id: str) -> str:

        user_data = await self.get_user_data(str(chat_id))
        if user_data:
            return user_data.get("language", "ru")
        return "ru"

    async def set_user_language(self, chat_id: str, language: str) -> None:

        user_data = await self.get_user_data(str(chat_id)) or {}
        user_data["language"] = language
        await self.save_user_data(str(chat_id), user_data)
