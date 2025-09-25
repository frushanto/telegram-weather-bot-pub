from typing import Callable, Dict, Optional, Tuple

import httpx

from ..core.exceptions import (
    ConfigurationError,
    GeocodeServiceError,
    WeatherQuotaExceededError,
    WeatherServiceError,
)
from ..domain.services import GeocodeService, WeatherService
from ..domain.weather import WeatherReport
from .weather_quota import WeatherApiQuotaManager


class OpenMeteoWeatherService(WeatherService):

    def __init__(self, quota_manager: WeatherApiQuotaManager) -> None:

        self._quota_manager = quota_manager

    async def get_weather(self, lat: float, lon: float) -> WeatherReport:

        try:
            reset_at = await self._quota_manager.try_consume()
            if reset_at is not None:
                raise WeatherQuotaExceededError(reset_at)

            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
                "timezone": "auto",
                "windspeed_unit": "ms",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                return WeatherReport.from_open_meteo(payload)
        except WeatherQuotaExceededError:
            raise
        except Exception as e:
            raise WeatherServiceError(f"Weather fetch error: {e}")


class NominatimGeocodeService(GeocodeService):

    async def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:

        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": city, "format": "json", "limit": 1, "addressdetails": 1}
            headers = {"User-Agent": "WeatherBot/1.0"}
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                if not data:
                    return None
                result = data[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                display_name = result.get("display_name", city)
                return lat, lon, display_name
        except Exception as e:
            raise GeocodeServiceError(f"Geocoding error: {e}")


WeatherServiceFactory = Callable[[WeatherApiQuotaManager], WeatherService]
GeocodeServiceFactory = Callable[[], GeocodeService]


WEATHER_SERVICE_FACTORIES: Dict[str, WeatherServiceFactory] = {
    "open-meteo": lambda quota: OpenMeteoWeatherService(quota)
}

GEOCODE_SERVICE_FACTORIES: Dict[str, GeocodeServiceFactory] = {
    "nominatim": NominatimGeocodeService,
}


def create_weather_service(
    provider: str, quota_manager: WeatherApiQuotaManager
) -> WeatherService:

    factory = WEATHER_SERVICE_FACTORIES.get(provider)
    if not factory:
        raise ConfigurationError(f"Unsupported weather service provider '{provider}'.")
    return factory(quota_manager)


def create_geocode_service(provider: str) -> GeocodeService:

    factory = GEOCODE_SERVICE_FACTORIES.get(provider)
    if not factory:
        raise ConfigurationError(f"Unsupported geocode service provider '{provider}'.")
    return factory()
