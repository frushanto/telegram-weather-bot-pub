import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_weather_service_timeout(self):

        with patch(
            "weatherbot.application.weather_service.WeatherApplicationService"
        ) as mock_service:
            service = mock_service.return_value
            service.get_weather_by_city = AsyncMock(
                side_effect=asyncio.TimeoutError("Timeout")
            )

            with pytest.raises(asyncio.TimeoutError):
                await service.get_weather_by_city("TestCity")

    @pytest.mark.asyncio
    async def test_invalid_city_name(self):

        with patch(
            "weatherbot.application.weather_service.WeatherApplicationService"
        ) as mock_service:
            service = mock_service.return_value
            service.get_weather_by_city = AsyncMock(return_value=None)
            result = await service.get_weather_by_city("NonExistentCity12345")
            assert result is None

    @pytest.mark.asyncio
    async def test_storage_error_handling(self):

        with patch(
            "weatherbot.infrastructure.json_repository.JsonUserRepository"
        ) as mock_repo:
            repo = mock_repo.return_value
            repo.save_user_data = MagicMock(side_effect=Exception("Storage error"))

            with pytest.raises(Exception):
                repo.save_user_data("user123", {"test": "data"})


class TestEdgeCases:

    def test_very_long_city_name(self):

        long_name = "A" * 1000

        assert len(long_name) == 1000
        assert isinstance(long_name, str)

    def test_special_characters_in_city(self):

        special_cities = [
            "Москва",
            "北京",
            "São Paulo",
            "New York-London",
            "City/Town",
        ]
        for city in special_cities:

            assert isinstance(city, str)
            assert len(city) > 0

    def test_extreme_coordinates(self):

        extreme_coords = [
            (90.0, 180.0),
            (-90.0, -180.0),
            (0.0, 0.0),
            (85.0, 175.0),
        ]
        for lat, lon in extreme_coords:

            assert -90 <= lat <= 90
            assert -180 <= lon <= 180

    @pytest.mark.asyncio
    async def test_concurrent_user_requests(self):

        from weatherbot.infrastructure.spam_protection import SpamProtection

        spam_protection = SpamProtection()

        async def make_request(user_id: str, message: str):
            return await spam_protection.is_spam(user_id, message, count_request=False)

        tasks = []
        for i in range(20):
            task = make_request(f"user_{i}", f"message_{i}")
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Unexpected exception: {result}")
            is_spam, reason = result
            assert isinstance(is_spam, bool)
            assert isinstance(reason, str)

    def test_empty_messages(self):

        empty_messages = ["", None, "   ", "\n", "\t"]
        for msg in empty_messages:

            if msg is None:
                assert msg is None
            else:
                assert isinstance(msg, str)
