from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.domain.conversation import ConversationMode
from weatherbot.handlers.commands import weather_cmd


class TestWeatherCommand:

    @pytest.mark.asyncio
    async def test_weather_command_basic(self):

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with (
            patch("weatherbot.handlers.commands.get_user_service") as mock_get_service,
            patch("weatherbot.handlers.commands.i18n") as mock_i18n,
            patch("weatherbot.handlers.commands.main_keyboard") as mock_keyboard,
        ):
            user_service = AsyncMock()
            mock_get_service.return_value = user_service
            user_service.get_user_language.return_value = "ru"
            mock_i18n.get.return_value = "Введите название города:"
            mock_keyboard.return_value = "test_keyboard"

            # Get the state store directly instead of patching
            from weatherbot.infrastructure.setup import get_conversation_state_store

            state_store = get_conversation_state_store()
            state_store.clear_conversation(123456)

            await weather_cmd(update, context)

            assert state_store.is_awaiting(
                123456, ConversationMode.AWAITING_CITY_WEATHER
            )

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
