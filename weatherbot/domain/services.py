from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

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
        self, user_id: int, message_text: str = "", user_lang: str = "ru"
    ) -> Tuple[bool, str]:

        pass

    @abstractmethod
    async def unblock_user(self, user_id: int) -> bool:

        pass

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> Dict:

        pass
