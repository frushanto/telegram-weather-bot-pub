import logging
from typing import Dict, Optional, Tuple

from ..core.exceptions import GeocodeServiceError, ValidationError, WeatherServiceError
from ..domain.services import GeocodeService, WeatherService

logger = logging.getLogger(__name__)


class WeatherApplicationService:

    def __init__(
        self, weather_service: WeatherService, geocode_service: GeocodeService
    ):
        self._weather_service = weather_service
        self._geocode_service = geocode_service

    async def get_weather_by_coordinates(self, lat: float, lon: float) -> Dict:

        try:
            if not (-90 <= lat <= 90):
                raise ValidationError(f"Invalid latitude: {lat}")
            if not (-180 <= lon <= 180):
                raise ValidationError(f"Invalid longitude: {lon}")
            weather_data = await self._weather_service.get_weather(lat, lon)
            logger.debug(f"Weather fetched for coordinates {lat}, {lon}")
            return weather_data
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error getting weather for coordinates {lat}, {lon}")
            raise WeatherServiceError(f"Failed to get weather: {e}")

    async def get_weather_by_city(self, city: str) -> Tuple[Dict, str]:

        try:
            if not city or not city.strip():
                raise ValidationError("City name cannot be empty")
            city = city.strip()

            geocode_result = await self._geocode_service.geocode_city(city)
            if not geocode_result:
                raise GeocodeServiceError(f"City '{city}' not found")
            lat, lon, label = geocode_result

            weather_data = await self._weather_service.get_weather(lat, lon)
            logger.info(f"Weather fetched for city {city} ({label})")
            return weather_data, label
        except (ValidationError, GeocodeServiceError):
            raise
        except Exception as e:
            logger.exception(f"Error getting weather for city {city}")
            raise WeatherServiceError(f"Failed to get weather for city: {e}")

    async def geocode_city(self, city: str) -> Optional[Tuple[float, float, str]]:

        try:
            if not city or not city.strip():
                raise ValidationError("City name cannot be empty")
            city = city.strip()
            result = await self._geocode_service.geocode_city(city)
            if result:
                logger.info(f"City geocoded {city}: {result[2]}")
            else:
                logger.warning(f"City {city} not found")
            return result
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error geocoding city {city}")
            raise GeocodeServiceError(f"Failed to find city: {e}")
