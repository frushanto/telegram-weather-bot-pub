import logging
from collections.abc import Iterable, Mapping
from typing import Optional

from ..core.exceptions import (
    GeocodeServiceError,
    ValidationError,
    WeatherQuotaExceededError,
    WeatherServiceError,
)
from ..domain.services import GeocodeService, WeatherService
from ..domain.weather import WeatherReport
from .dtos import CityWeatherDTO, GeocodeResultDTO

logger = logging.getLogger(__name__)


class WeatherApplicationService:

    def __init__(
        self, weather_service: WeatherService, geocode_service: GeocodeService
    ):
        self._weather_service = weather_service
        self._geocode_service = geocode_service

    async def get_weather_by_coordinates(self, lat: float, lon: float) -> WeatherReport:

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
        except WeatherQuotaExceededError:
            raise
        except Exception as e:
            logger.exception(f"Error getting weather for coordinates {lat}, {lon}")
            raise WeatherServiceError(f"Failed to get weather: {e}")

    async def get_weather_by_city(self, city: str) -> CityWeatherDTO:

        try:
            if not city or not city.strip():
                raise ValidationError("City name cannot be empty")
            city = city.strip()

            geocode_result = await self._geocode_service.geocode_city(city)
            if not geocode_result:
                raise GeocodeServiceError(f"City '{city}' not found")
            location = self._normalize_geocode_result(geocode_result)

            weather_data = await self._weather_service.get_weather(
                location.lat, location.lon
            )
            logger.info(
                "Weather fetched for city %s (%s)", city, location.label or city
            )

            return CityWeatherDTO(report=weather_data, location=location)
        except (ValidationError, GeocodeServiceError):
            raise
        except WeatherQuotaExceededError:
            raise
        except Exception as e:
            logger.exception(f"Error getting weather for city {city}")
            raise WeatherServiceError(f"Failed to get weather for city: {e}")

    async def geocode_city(self, city: str) -> Optional[GeocodeResultDTO]:

        try:
            if not city or not city.strip():
                raise ValidationError("City name cannot be empty")
            city = city.strip()
            result = await self._geocode_service.geocode_city(city)
            if result:
                location = self._normalize_geocode_result(result)
                logger.info("City geocoded %s: %s", city, location.label or city)
                return location
            else:
                logger.warning(f"City {city} not found")
            return None
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error geocoding city {city}")
            raise GeocodeServiceError(f"Failed to find city: {e}")

    @staticmethod
    def _normalize_geocode_result(result: object) -> GeocodeResultDTO:
        """Convert various result shapes into :class:`GeocodeResultDTO`."""

        if isinstance(result, GeocodeResultDTO):
            return GeocodeResultDTO(
                lat=float(result.lat),
                lon=float(result.lon),
                label=result.label or "",
            )

        if isinstance(result, Mapping):
            lat = float(result["lat"])  # type: ignore[index]
            lon = float(result["lon"])  # type: ignore[index]
            label = str(result.get("label", ""))  # type: ignore[index]
            return GeocodeResultDTO(lat=lat, lon=lon, label=label)

        if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
            items = list(result)
            if len(items) >= 3:
                lat, lon, label = items[:3]
                return GeocodeResultDTO(
                    lat=float(lat), lon=float(lon), label=str(label or "")
                )

        if all(hasattr(result, attr) for attr in ("lat", "lon")):
            lat = float(getattr(result, "lat"))
            lon = float(getattr(result, "lon"))
            label = str(getattr(result, "label", ""))
            return GeocodeResultDTO(lat=lat, lon=lon, label=label)

        lat, lon, label = result  # type: ignore[misc]
        return GeocodeResultDTO(lat=float(lat), lon=float(lon), label=str(label or ""))
