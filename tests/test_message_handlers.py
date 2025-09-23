from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.handlers.messages import on_location, on_text


@pytest.mark.asyncio
async def test_on_location_success():

    update = MagicMock()
    update.message.location.latitude = 55.7558
    update.message.location.longitude = 37.6176
    update.effective_chat.id = 123456
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    mock_weather_data = {"temperature": 15, "description": "облачно", "place": "Москва"}
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

    weather_service = AsyncMock()
    weather_data = {"temperature": 15, "description": "ясно"}
    weather_service.get_weather_by_city.return_value = (weather_data, None)

    from weatherbot.infrastructure.state import awaiting_city_weather

    awaiting_city_weather[123456] = True

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


@pytest.mark.asyncio
async def test_on_text_set_home():

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
