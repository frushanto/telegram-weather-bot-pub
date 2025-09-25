from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.core.exceptions import WeatherQuotaExceededError
from weatherbot.domain.value_objects import UserHome, UserProfile
from weatherbot.domain.weather import WeatherCurrent, WeatherDaily, WeatherReport
from weatherbot.handlers.messages import on_location, on_text


@pytest.fixture(autouse=True)
def patch_quota_notifier(monkeypatch):

    mock_notifier = AsyncMock()
    monkeypatch.setattr(
        "weatherbot.handlers.messages.notify_quota_if_needed", mock_notifier
    )
    return mock_notifier


@pytest.mark.asyncio
async def test_on_location_success():

    update = MagicMock()
    update.message.location.latitude = 55.7558
    update.message.location.longitude = 37.6176
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_weather_data = _make_report()
    with (
        patch("weatherbot.handlers.messages.get_user_service") as mock_user_service,
        patch(
            "weatherbot.handlers.messages.get_weather_application_service"
        ) as mock_weather_service,
        patch("weatherbot.handlers.messages.format_weather") as mock_format,
        patch("weatherbot.handlers.messages.main_keyboard") as mock_keyboard,
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        user_service.get_user_profile.return_value = _make_profile()
        mock_user_service.return_value = user_service
        weather_service = AsyncMock()
        weather_service.get_weather_by_coordinates.return_value = mock_weather_data
        mock_weather_service.return_value = weather_service
        mock_format.return_value = "Москва: 15°C, облачно"
        mock_keyboard.return_value = None
        await on_location(update, context)

    weather_service.get_weather_by_coordinates.assert_awaited_once_with(
        55.7558, 37.6176
    )
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_location_weather_error():

    update = MagicMock()
    update.message.location.latitude = 55.7558
    update.message.location.longitude = 37.6176
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with (
        patch("weatherbot.handlers.messages.get_user_service") as mock_user_service,
        patch(
            "weatherbot.handlers.messages.get_weather_application_service"
        ) as mock_weather_service,
        patch("weatherbot.handlers.messages.i18n.get") as mock_i18n,
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        mock_user_service.return_value = user_service
        weather_service = AsyncMock()
        from weatherbot.core.exceptions import WeatherServiceError

        weather_service.get_weather_by_coordinates.side_effect = WeatherServiceError(
            "API недоступен"
        )
        mock_weather_service.return_value = weather_service
        mock_i18n.return_value = "Ошибка получения погоды"
        await on_location(update, context)

    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_location_quota_exceeded():

    update = MagicMock()
    update.message.location.latitude = 55.7558
    update.message.location.longitude = 37.6176
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    reset_at = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    with (
        patch("weatherbot.handlers.messages.get_user_service") as mock_user_service,
        patch(
            "weatherbot.handlers.messages.get_weather_application_service"
        ) as mock_weather_service,
        patch("weatherbot.handlers.messages.i18n.get") as mock_i18n,
        patch("weatherbot.handlers.messages.main_keyboard") as mock_keyboard,
        patch("weatherbot.handlers.messages.format_reset_time") as mock_format_reset,
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        user_service.get_user_profile.return_value = _make_profile()
        mock_user_service.return_value = user_service

        weather_service = AsyncMock()
        weather_service.get_weather_by_coordinates.side_effect = (
            WeatherQuotaExceededError(reset_at)
        )
        mock_weather_service.return_value = weather_service

        mock_format_reset.return_value = "formatted-reset"

        def fake_i18n(key, lang, **kwargs):

            if key == "weather_quota_exceeded":
                return f"quota message {kwargs.get('reset_time')}"
            return key

        mock_i18n.side_effect = fake_i18n
        mock_keyboard.return_value = None

        await on_location(update, context)

    mock_format_reset.assert_called_once_with(reset_at, "Europe/Moscow")
    mock_i18n.assert_called_once_with(
        "weather_quota_exceeded", "ru", reset_time="formatted-reset"
    )
    update.message.reply_text.assert_awaited_once_with(
        "quota message formatted-reset", reply_markup=None
    )


@pytest.mark.asyncio
async def test_on_text_city_weather():
    from weatherbot.handlers import messages

    """Тестирует обработку текста с названием города"""
    update = MagicMock()
    update.message.text = "Москва"
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()

    context = MagicMock()

    user_service = AsyncMock()
    user_service.get_user_language.return_value = "ru"
    user_service.get_user_profile.return_value = _make_profile()

    weather_service = AsyncMock()
    weather_data = _make_report()
    weather_service.get_weather_by_city.return_value = (weather_data, None)

    from weatherbot.domain.conversation import ConversationMode
    from weatherbot.infrastructure.state import (
        awaiting_city_weather,
        conversation_manager,
    )

    conversation_manager.set_awaiting_mode(
        123456, ConversationMode.AWAITING_CITY_WEATHER
    )
    awaiting_city_weather[123456] = True  # Legacy compatibility

    with (
        patch(
            "weatherbot.handlers.messages.get_user_service", return_value=user_service
        ),
        patch(
            "weatherbot.handlers.messages.get_weather_application_service",
            return_value=weather_service,
        ),
        patch(
            "weatherbot.handlers.messages.format_weather",
            return_value="Москва: 15°C, ясно",
        ),
        patch("weatherbot.handlers.messages.main_keyboard", return_value=None),
    ):
        await messages.on_text(update, context)

    weather_service.get_weather_by_city.assert_awaited_once_with("Москва")
    update.message.reply_text.assert_awaited_once()

    assert 123456 not in awaiting_city_weather
    assert not conversation_manager.is_awaiting(
        123456, ConversationMode.AWAITING_CITY_WEATHER
    )


@pytest.mark.asyncio
async def test_on_text_set_home():
    from weatherbot.domain.conversation import ConversationMode
    from weatherbot.infrastructure.state import conversation_manager

    conversation_manager.set_awaiting_mode(123456, ConversationMode.AWAITING_SETHOME)

    with (
        patch("weatherbot.handlers.messages.awaiting_sethome", {123456: True}),
        patch("weatherbot.handlers.messages.last_location_by_chat", {}),
        patch("weatherbot.handlers.messages.get_user_service") as mock_user_service,
        patch(
            "weatherbot.handlers.messages.get_weather_application_service"
        ) as mock_weather_service,
    ):
        update = MagicMock()
        update.message.text = "Санкт-Петербург"
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        user_service.set_user_home = AsyncMock()
        mock_user_service.return_value = user_service

        weather_service = AsyncMock()
        weather_service.geocode_city = AsyncMock(
            return_value=(59.9311, 30.3609, "Санкт-Петербург, Россия")
        )
        mock_weather_service.return_value = weather_service

        with patch(
            "weatherbot.handlers.messages.i18n.get", return_value="Дом установлен"
        ):
            await on_text(update, context)

        weather_service.geocode_city.assert_awaited_once_with("Санкт-Петербург")
        user_service.set_user_home.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_text_keyboard_buttons():

    test_cases = [
        ("☁️ Погода по городу", "weather_prompt"),
        ("🏠 Погода дома", "home_weather"),
        ("➕ Задать дом", "sethome_prompt"),
        ("🗑 Удалить дом", "unsethome"),
        ("ℹ️ Помощь", "help_message"),
    ]
    for button_text, expected_action in test_cases:
        update = MagicMock()
        update.message.text = button_text
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch(
            "weatherbot.handlers.messages.get_user_service"
        ) as mock_user_service:
            user_service = AsyncMock()
            user_service.get_user_language.return_value = "ru"
            mock_user_service.return_value = user_service
            with patch(
                "weatherbot.handlers.messages.i18n.get",
                return_value=f"Ответ на {expected_action}",
            ):
                await on_text(update, context)

        update.message.reply_text.assert_awaited()
        update.message.reply_text.reset_mock()


@pytest.mark.asyncio
async def test_on_text_unknown_message():

    update = MagicMock()
    update.message.text = "Какой-то случайный текст"
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    with (
        patch("weatherbot.handlers.messages.get_user_service") as mock_user_service,
        patch("weatherbot.handlers.messages.i18n.get") as mock_i18n,
    ):
        user_service = AsyncMock()
        user_service.get_user_language.return_value = "ru"
        mock_user_service.return_value = user_service
        mock_i18n.return_value = "Не понимаю команду"
        await on_text(update, context)

    update.message.reply_text.assert_awaited_once()


def _make_report(temperature: float = 15.0) -> WeatherReport:

    return WeatherReport(
        current=WeatherCurrent(
            temperature=temperature,
            apparent_temperature=temperature - 1,
            wind_speed=4.0,
            weather_code=1,
        ),
        daily=[
            WeatherDaily(
                min_temperature=temperature - 5,
                max_temperature=temperature + 5,
                precipitation_probability=20.0,
                sunrise="2025-01-01T06:00",
                sunset="2025-01-01T18:00",
                wind_speed_max=8.0,
                weather_code=2,
            )
        ],
    )


def _make_profile(timezone: str | None = "Europe/Moscow") -> UserProfile:

    home = UserHome(
        lat=55.0,
        lon=37.0,
        label="Test",
        timezone=timezone,
    )
    return UserProfile(language="ru", language_explicit=True, home=home)
