from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from .weather import WeatherReport


class WeatherService(ABC):

    @abstractmethod
    async def get_weather(self, lat: float, lon: float) -> WeatherReport:

        pass


class GeocodeService(ABC):

    @abstractmethod
    async def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:

        pass


class SpamProtectionService(ABC):

    @abstractmethod
    async def is_spam(
        self,
        user_id: int,
        message_text: str = "",
        *,
        count_request: bool = True,
        user_lang: str = "ru",
    ) -> Tuple[bool, str]:

        pass

    @abstractmethod
    async def unblock_user(self, user_id: int) -> bool:

        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> Dict:

        pass

    @abstractmethod
    def get_user_activity_snapshot(self) -> Mapping[int, Any]:

        pass

    @abstractmethod
    def get_blocked_users(self) -> Iterable[int]:

        pass

    @abstractmethod
    async def cleanup_old_data(self) -> None:

        pass
