from abc import ABC, abstractmethod
from typing import Dict, Optional


class UserRepository(ABC):

    @abstractmethod
    async def get_user_data(self, chat_id: str) -> Optional[Dict]:

        pass

    @abstractmethod
    async def save_user_data(self, chat_id: str, data: Dict) -> None:

        pass

    @abstractmethod
    async def delete_user_data(self, chat_id: str) -> bool:

        pass

    @abstractmethod
    async def get_all_users(self) -> Dict[str, Dict]:

        pass

    @abstractmethod
    async def get_user_language(self, chat_id: str) -> str:

        pass

    @abstractmethod
    async def set_user_language(self, chat_id: str, language: str) -> None:

        pass
