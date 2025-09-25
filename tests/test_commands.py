import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.application.subscription_service import SubscriptionService
from weatherbot.application.user_service import UserService
from weatherbot.application.weather_service import WeatherApplicationService
from weatherbot.domain.value_objects import UserHome, UserProfile, UserSubscription
from weatherbot.domain.weather import WeatherCurrent, WeatherDaily, WeatherReport
from weatherbot.handlers.commands import (
    data_cmd,
    delete_me_cmd,
    help_cmd,
    home_cmd,
    language_cmd,
    privacy_cmd,
    sethome_cmd,
    start_cmd,
    subscribe_cmd,
    unsethome_cmd,
    unsubscribe_cmd,
    whoami_cmd,
)
from weatherbot.infrastructure.json_repository import JsonUserRepository


@pytest.fixture(autouse=True)
def patch_commands_quota_notifier(monkeypatch):

    mock_notifier = AsyncMock()
    monkeypatch.setattr(
        "weatherbot.handlers.commands.notify_quota_if_needed", mock_notifier
    )
    return mock_notifier


@pytest.mark.asyncio
async def test_start_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_user_service.get_user_profile.return_value = UserProfile()
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch("weatherbot.handlers.commands.i18n.get", return_value="Привет!"):
            with patch(
                "weatherbot.handlers.commands.language_keyboard", return_value=None
            ):
                with patch(
                    "weatherbot.handlers.commands.main_keyboard", return_value=None
                ):
                    await start_cmd(update, context)

    mock_user_service.get_user_language.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_cmd_language_set():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "en"
    mock_user_service.get_user_profile.return_value = UserProfile(
        language="en", language_explicit=True
    )
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch("weatherbot.handlers.commands.i18n.get", return_value="Hello"):
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                with patch(
                    "weatherbot.handlers.commands.language_keyboard", return_value=None
                ):
                    await start_cmd(update, context)

    mock_user_service.get_user_language.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_sethome_cmd_success():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["Москва"]

    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_weather_service = AsyncMock()
    mock_weather_service.geocode_city.return_value = (
        55.7558,
        37.6176,
        "Москва, Россия",
    )
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.get_weather_application_service",
            return_value=mock_weather_service,
        ):
            with patch(
                "weatherbot.handlers.commands.i18n.get", return_value="Дом установлен"
            ):
                with patch(
                    "weatherbot.handlers.commands.main_keyboard", return_value=None
                ):
                    await sethome_cmd(update, context)

    mock_weather_service.geocode_city.assert_awaited_once_with("Москва")
    mock_user_service.set_user_home.assert_awaited_once_with(
        "123456", 55.7558, 37.6176, "Москва, Россия"
    )
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_sethome_cmd_no_args():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = []
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.i18n.get", return_value="Укажите город"
        ):
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await sethome_cmd(update, context)

    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_home_cmd_with_home():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_user_service.get_user_home.return_value = UserHome(
        lat=55.7558, lon=37.6176, label="Москва"
    )
    mock_weather_service = AsyncMock()
    mock_weather_service.get_weather_by_coordinates.return_value = _sample_report()
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.get_weather_application_service",
            return_value=mock_weather_service,
        ):
            with patch(
                "weatherbot.handlers.commands.format_weather",
                return_value="Погода: 20°C",
            ):
                with patch(
                    "weatherbot.handlers.commands.main_keyboard", return_value=None
                ):
                    await home_cmd(update, context)

    mock_user_service.get_user_home.assert_awaited_once_with("123456")
    mock_weather_service.get_weather_by_coordinates.assert_awaited_once_with(
        55.7558, 37.6176
    )
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_home_cmd_no_home():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_user_service.get_user_home.return_value = None
    mock_weather_service = AsyncMock()
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.get_weather_application_service",
            return_value=mock_weather_service,
        ):
            with patch(
                "weatherbot.handlers.commands.i18n.get",
                return_value="Дом не установлен",
            ):
                with patch(
                    "weatherbot.handlers.commands.main_keyboard", return_value=None
                ):
                    await home_cmd(update, context)

    mock_user_service.get_user_home.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscribe_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["8:30"]
    context.application.job_queue = MagicMock()

    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_subscription_service = AsyncMock()
    mock_subscription_service.parse_time_string.return_value = (8, 30)
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.get_subscription_service",
            return_value=mock_subscription_service,
        ):
            with patch("weatherbot.handlers.commands.schedule_daily_timezone_aware"):
                with patch(
                    "weatherbot.handlers.commands.i18n.get",
                    return_value="Подписка установлена",
                ):
                    with patch(
                        "weatherbot.handlers.commands.main_keyboard", return_value=None
                    ):
                        await subscribe_cmd(update, context)

    mock_subscription_service.parse_time_string.assert_awaited_once_with("8:30")
    mock_subscription_service.set_subscription.assert_awaited_once_with("123456", 8, 30)
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_language_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["en"]
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.i18n.get", return_value="Language changed"
        ):
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await language_cmd(update, context)

    mock_user_service.set_user_language.assert_awaited_once_with("123456", "en")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsubscribe_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.application.job_queue.get_jobs_by_name.return_value = []
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_subscription_service = AsyncMock()
    mock_subscription_service.remove_subscription.return_value = True
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.get_subscription_service",
            return_value=mock_subscription_service,
        ):
            with patch(
                "weatherbot.handlers.commands.i18n.get",
                return_value="Подписка отменена",
            ):
                with patch(
                    "weatherbot.handlers.commands.main_keyboard", return_value=None
                ):
                    await unsubscribe_cmd(update, context)

    mock_subscription_service.remove_subscription.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_data_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_user_service.get_user_profile.return_value = UserProfile(
        language="ru",
        home=UserHome(
            lat=55.7558, lon=37.6176, label="Москва", timezone="Europe/Moscow"
        ),
        subscription=UserSubscription(hour=8, minute=30),
    )
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch("weatherbot.handlers.commands.i18n.get") as mock_i18n:
            mock_i18n.side_effect = lambda key, lang, **kwargs: key
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await data_cmd(update, context)

    mock_user_service.get_user_profile.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_me_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    mock_user_service.delete_user_data.return_value = True
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.i18n.get", return_value="Данные удалены"
        ):
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await delete_me_cmd(update, context)

    mock_user_service.delete_user_data.assert_awaited_once_with("123456")
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_whoami_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.effective_user.id = 123456
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"
    update.effective_user.username = "testuser"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch("weatherbot.handlers.commands.i18n.get") as mock_i18n:
            mock_i18n.side_effect = lambda key, lang, **kwargs: key
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await whoami_cmd(update, context)

    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_privacy_cmd():

    update = MagicMock()
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_user_service = AsyncMock()
    mock_user_service.get_user_language.return_value = "ru"
    with patch(
        "weatherbot.handlers.commands.get_user_service", return_value=mock_user_service
    ):
        with patch(
            "weatherbot.handlers.commands.i18n.get", return_value="Privacy info"
        ):
            with patch("weatherbot.handlers.commands.main_keyboard", return_value=None):
                await privacy_cmd(update, context)

    update.message.reply_text.assert_awaited_once()


def _sample_report(temp: float = 20.0) -> WeatherReport:
    return WeatherReport(
        current=WeatherCurrent(
            temperature=temp,
            apparent_temperature=temp - 2,
            wind_speed=5.0,
            weather_code=0,
        ),
        daily=[
            WeatherDaily(
                min_temperature=temp - 5,
                max_temperature=temp + 5,
                precipitation_probability=30.0,
                sunrise="2025-01-01T06:00",
                sunset="2025-01-01T18:00",
                wind_speed_max=7.0,
                weather_code=1,
            )
        ],
    )
