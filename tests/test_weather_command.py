from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.handlers.commands import weather_cmd


class TestWeatherCommand:

    @pytest.mark.asyncio
    async def test_weather_command_basic(self):

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        mock_awaiting = {}
        with (
            patch("weatherbot.handlers.commands.get_user_service") as mock_get_service,
            patch("weatherbot.handlers.messages.awaiting_city_weather", mock_awaiting),
            patch("weatherbot.handlers.commands.i18n") as mock_i18n,
            patch("weatherbot.handlers.commands.main_keyboard") as mock_keyboard,
        ):
            user_service = AsyncMock()
            mock_get_service.return_value = user_service
            user_service.get_user_language.return_value = "ru"
            mock_i18n.get.return_value = "Введите название города:"
            mock_keyboard.return_value = "test_keyboard"
            await weather_cmd(update, context)

            assert 123456 in mock_awaiting
            assert mock_awaiting[123456] is True

            update.message.reply_text.assert_called_once_with(
                "Введите название города:", reply_markup="test_keyboard"
            )

    @pytest.mark.asyncio
    async def test_weather_command_with_language(self):

        for lang in ["ru", "en", "de"]:
            update = MagicMock()
            update.effective_chat.id = 123456
            update.message.reply_text = AsyncMock()
            context = MagicMock()
            with (
                patch(
                    "weatherbot.handlers.commands.get_user_service"
                ) as mock_get_service,
                patch(
                    "weatherbot.handlers.commands.awaiting_city_weather"
                ) as mock_awaiting,
                patch("weatherbot.handlers.commands.i18n") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard") as mock_keyboard,
            ):
                user_service = AsyncMock()
                mock_get_service.return_value = user_service
                user_service.get_user_language.return_value = lang
                mock_i18n.get.return_value = "Enter city name:"
                mock_keyboard.return_value = "test_keyboard"
                await weather_cmd(update, context)

                mock_i18n.get.assert_called_with("enter_city", lang)

    @pytest.mark.asyncio
    async def test_weather_command_error_handling(self):

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        with patch("weatherbot.handlers.commands.get_user_service") as mock_get_service:

            user_service = AsyncMock()
            mock_get_service.return_value = user_service
            user_service.get_user_language.side_effect = Exception("Test error")

            try:
                await weather_cmd(update, context)

                assert True, "Декоратор успешно перехватил исключение"
            except Exception as e:
                assert False, f"Декоратор не перехватил исключение: {e}"
