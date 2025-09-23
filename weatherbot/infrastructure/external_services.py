from typing import Dict, Optional, Tuple

import httpx

from ..core.exceptions import GeocodeServiceError, WeatherServiceError
from ..domain.services import GeocodeService, WeatherService


class OpenMeteoWeatherService(WeatherService):

    async def get_weather(self, lat: float, lon: float) -> Dict:

        try:
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
                return response.json()
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
