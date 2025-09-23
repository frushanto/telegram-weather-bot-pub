import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.application.weather_service import WeatherApplicationService
from weatherbot.core.config import BotConfig, SpamConfig
from weatherbot.core.container import Container
from weatherbot.core.exceptions import StorageError, ValidationError
from weatherbot.domain.repositories import UserRepository
from weatherbot.domain.services import (
    GeocodeService,
    SpamProtectionService,
    WeatherService,
)
from weatherbot.infrastructure.external_services import (
    NominatimGeocodeService,
    OpenMeteoWeatherService,
)
from weatherbot.infrastructure.json_repository import JsonUserRepository


@pytest.mark.asyncio
async def test_container_setup():

    test_config = BotConfig(
        token="test_token", admin_ids=[123456], spam_config=SpamConfig()
    )
    with patch("weatherbot.core.config._config", test_config):
        container = Container()
        container.clear()

        container.register_singleton(UserRepository, JsonUserRepository())
        container.register_singleton(WeatherService, OpenMeteoWeatherService())
        container.register_singleton(GeocodeService, NominatimGeocodeService())

        user_repo = container.get(UserRepository)
        weather_service = container.get(WeatherService)
        geocode_service = container.get(GeocodeService)
        assert user_repo is not None
        assert weather_service is not None
        assert geocode_service is not None


@pytest.mark.asyncio
async def test_user_repository():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    try:
        user_repo = JsonUserRepository(temp_path)

        test_chat_id = "test_123"
        test_data = {"lat": 55.7558, "lon": 37.6176, "label": "Москва"}

        await user_repo.save_user_data(test_chat_id, test_data)

        retrieved_data = await user_repo.get_user_data(test_chat_id)
        assert retrieved_data == test_data

        deleted = await user_repo.delete_user_data(test_chat_id)
        assert deleted is True

        retrieved_data = await user_repo.get_user_data(test_chat_id)
        assert retrieved_data is None
    finally:

        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_language_operations():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    try:
        user_repo = JsonUserRepository(temp_path)
        test_chat_id = "test_lang_123"

        lang = await user_repo.get_user_language(test_chat_id)
        assert lang == "ru"

        await user_repo.set_user_language(test_chat_id, "en")
        lang = await user_repo.get_user_language(test_chat_id)
        assert lang == "en"

        await user_repo.delete_user_data(test_chat_id)
    finally:

        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_user_service():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    try:
        user_repo = JsonUserRepository(temp_path)
        user_service = UserService(user_repo)
        test_chat_id = "test_user_service"

        await user_service.set_user_home(test_chat_id, 55.7558, 37.6176, "Москва")

        home = await user_service.get_user_home(test_chat_id)
        assert home is not None
        assert home["lat"] == 55.7558
        assert home["lon"] == 37.6176
        assert home["label"] == "Москва"

        with pytest.raises(ValidationError):
            await user_service.set_user_home(test_chat_id, 91.0, 0, "Неверная широта")

        removed = await user_service.remove_user_home(test_chat_id)
        assert removed is True

        home = await user_service.get_user_home(test_chat_id)
        assert home is None
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_subscription_service():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    try:
        user_repo = JsonUserRepository(temp_path)
        subscription_service = SubscriptionService(user_repo)
        test_chat_id = "test_subscription"

        subscription = await subscription_service.get_subscription(test_chat_id)
        assert subscription is None

        await subscription_service.set_subscription(test_chat_id, 8, 30)

        subscription = await subscription_service.get_subscription(test_chat_id)
        assert subscription == (8, 30)

        with pytest.raises(ValidationError):
            await subscription_service.set_subscription(test_chat_id, 25, 0)

        removed = await subscription_service.remove_subscription(test_chat_id)
        assert removed is True

        subscription = await subscription_service.get_subscription(test_chat_id)
        assert subscription is None
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_subscription_service_time_parsing():

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    try:
        user_repo = JsonUserRepository(temp_path)
        subscription_service = SubscriptionService(user_repo)

        assert await subscription_service.parse_time_string("8:30") == (8, 30)
        assert await subscription_service.parse_time_string("08:00") == (8, 0)
        assert await subscription_service.parse_time_string("9") == (9, 0)
        assert await subscription_service.parse_time_string("23:59") == (23, 59)

        with pytest.raises(ValidationError):
            await subscription_service.parse_time_string("25:00")
        with pytest.raises(ValidationError):
            await subscription_service.parse_time_string("abc")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_weather_application_service():

    mock_weather_service = AsyncMock()
    mock_geocode_service = AsyncMock()
    weather_app_service = WeatherApplicationService(
        mock_weather_service, mock_geocode_service
    )

    mock_weather_data = {"temperature": 20, "weather_code": 0}
    mock_weather_service.get_weather.return_value = mock_weather_data
    mock_geocode_service.geocode_city.return_value = (55.7558, 37.6176, "Москва")

    weather = await weather_app_service.get_weather_by_coordinates(55.7558, 37.6176)
    assert weather == mock_weather_data

    weather, label = await weather_app_service.get_weather_by_city("Москва")
    assert weather == mock_weather_data
    assert label == "Москва"

    with pytest.raises(ValidationError):
        await weather_app_service.get_weather_by_coordinates(91.0, 0)
