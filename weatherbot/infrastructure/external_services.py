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

DEFAULT_TIMEOUT = 10.0


class OpenMeteoWeatherService(WeatherService):

    def __init__(
        self,
        quota_manager: WeatherApiQuotaManager,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:

        self._quota_manager = quota_manager
        self._http_client = http_client

    async def _request_weather(
        self, client: httpx.AsyncClient, lat: float, lon: float
    ) -> WeatherReport:

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto",
            "windspeed_unit": "ms",
        }
        response = await client.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        return WeatherReport.from_open_meteo(payload)

    async def get_weather(self, lat: float, lon: float) -> WeatherReport:

        try:
            reset_at = await self._quota_manager.try_consume()
            if reset_at is not None:
                raise WeatherQuotaExceededError(reset_at)

            if self._http_client is None:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                    return await self._request_weather(client, lat, lon)

            return await self._request_weather(self._http_client, lat, lon)
        except WeatherQuotaExceededError:
            raise
        except Exception as e:
            raise WeatherServiceError(f"Weather fetch error: {e}")


class NominatimGeocodeService(GeocodeService):

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:

        self._http_client = http_client

    async def _perform_request(
        self, client: httpx.AsyncClient, city: str
    ) -> Optional[Tuple[float, float, str]]:

        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1, "addressdetails": 1}
        headers = {"User-Agent": "WeatherBot/1.0"}
        response = await client.get(
            url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        result = data[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        display_name = result.get("display_name", city)
        return lat, lon, display_name

    async def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:

        try:
            if self._http_client is None:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                    return await self._perform_request(client, city)

            return await self._perform_request(self._http_client, city)
        except Exception as e:
            raise GeocodeServiceError(f"Geocoding error: {e}")


WeatherServiceFactory = Callable[
    [WeatherApiQuotaManager, Optional[httpx.AsyncClient]], WeatherService
]
GeocodeServiceFactory = Callable[[Optional[httpx.AsyncClient]], GeocodeService]


WEATHER_SERVICE_FACTORIES: Dict[str, WeatherServiceFactory] = {
    "open-meteo": lambda quota, client=None: OpenMeteoWeatherService(
        quota, http_client=client
    )
}

GEOCODE_SERVICE_FACTORIES: Dict[str, GeocodeServiceFactory] = {
    "nominatim": lambda client=None: NominatimGeocodeService(http_client=client),
}


def create_weather_service(
    provider: str,
    quota_manager: WeatherApiQuotaManager,
    http_client: Optional[httpx.AsyncClient] = None,
) -> WeatherService:

    factory = WEATHER_SERVICE_FACTORIES.get(provider)
    if not factory:
        raise ConfigurationError(f"Unsupported weather service provider '{provider}'.")
    return factory(quota_manager, http_client)


def create_geocode_service(
    provider: str, http_client: Optional[httpx.AsyncClient] = None
) -> GeocodeService:

    factory = GEOCODE_SERVICE_FACTORIES.get(provider)
    if not factory:
        raise ConfigurationError(f"Unsupported geocode service provider '{provider}'.")
    return factory(http_client)
