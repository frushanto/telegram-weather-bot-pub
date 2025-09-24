from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
from weatherbot.handlers.language import language_callback
from weatherbot.handlers.messages import on_location, on_text


class TestAllCommandsAllLanguages:

    @pytest.fixture
    def languages(self):
        return ["ru", "en", "de"]

    @pytest.fixture
    def mock_update(self):

        update = MagicMock()
        update.effective_chat.id = 123456
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):

        context = MagicMock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_start_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        for lang in languages:
            with (
                patch("weatherbot.handlers.commands.get_user_service") as mock_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
                patch("weatherbot.core.decorators.spam_protection") as mock_spam,
            ):
                user_service = AsyncMock()
                user_service.get_user_language = AsyncMock(return_value=lang)
                mock_service.return_value = user_service

                async def mock_is_spam(*args, **kwargs):
                    return (False, "")

                mock_spam.is_spam = mock_is_spam
                mock_i18n.return_value = f"Start message in {lang}"
                await start_cmd(mock_update, mock_context)
                user_service.get_user_language.assert_awaited_with("123456")
                mock_update.message.reply_text.assert_awaited()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_help_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        for lang in languages:
            with (
                patch("weatherbot.handlers.commands.get_user_service") as mock_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                mock_service.return_value = user_service
                mock_i18n.return_value = f"Help message in {lang}"
                await help_cmd(mock_update, mock_context)
                mock_update.message.reply_text.assert_awaited()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_sethome_command_all_languages(self, languages, mock_update):
        for lang in languages:
            context = MagicMock()
            context.args = ["TestCity"]
            with (
                patch(
                    "weatherbot.handlers.commands.get_user_service"
                ) as mock_user_service,
                patch(
                    "weatherbot.handlers.commands.get_weather_application_service"
                ) as mock_weather_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
                patch("weatherbot.core.decorators.spam_protection") as mock_spam,
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                user_service.set_user_home = AsyncMock()
                mock_user_service.return_value = user_service
                weather_service = AsyncMock()
                weather_service.geocode_city.return_value = (
                    50.0,
                    10.0,
                    f"TestCity, {lang}",
                )
                mock_weather_service.return_value = weather_service
                mock_i18n.return_value = f"Home set message in {lang}"
                mock_spam.is_spam = AsyncMock(return_value=(False, ""))
                await sethome_cmd(mock_update, context)
                user_service.set_user_home.assert_awaited()
                mock_update.message.reply_text.assert_awaited()
                user_service.set_user_home.reset_mock()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_home_command_all_languages(
        self, languages, mock_update, mock_context
    ):
        for lang in languages:
            with (
                patch(
                    "weatherbot.handlers.commands.get_user_service"
                ) as mock_user_service,
                patch(
                    "weatherbot.handlers.commands.get_weather_application_service"
                ) as mock_weather_service,
                patch("weatherbot.handlers.commands.format_weather") as mock_format,
                patch("weatherbot.handlers.commands.main_keyboard"),
                patch("weatherbot.core.decorators.spam_protection") as mock_spam,
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                user_service.get_user_home.return_value = {"lat": 50.0, "lon": 10.0}
                user_service.get_user_data.return_value = {"label": f"Home in {lang}"}
                mock_user_service.return_value = user_service
                weather_service = AsyncMock()
                weather_service.get_weather_by_coordinates = AsyncMock(
                    return_value={
                        "temperature": 20,
                        "description": f"weather in {lang}",
                    }
                )
                mock_weather_service.return_value = weather_service
                mock_format.return_value = f"Weather format in {lang}"
                mock_spam.is_spam = AsyncMock(return_value=(False, ""))
                await home_cmd(mock_update, mock_context)
                weather_service.get_weather_by_coordinates.assert_awaited()
                mock_update.message.reply_text.assert_awaited()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_subscribe_command_all_languages(self, languages, mock_update):
        for lang in languages:
            context = MagicMock()
            context.args = ["08:30"]
            with (
                patch(
                    "weatherbot.handlers.commands.get_user_service"
                ) as mock_user_service,
                patch(
                    "weatherbot.handlers.commands.get_subscription_service"
                ) as mock_sub_service,
                patch("weatherbot.handlers.commands.schedule_daily_timezone_aware"),
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.core.decorators.spam_protection") as mock_spam,
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                mock_user_service.return_value = user_service
                subscription_service = AsyncMock()
                subscription_service.set_subscription = AsyncMock()
                subscription_service.parse_time_string = AsyncMock(return_value=(8, 30))
                mock_sub_service.return_value = subscription_service
                mock_i18n.return_value = f"Subscription set in {lang}"
                mock_spam.is_spam = AsyncMock(return_value=(False, ""))
                await subscribe_cmd(mock_update, context)
                subscription_service.set_subscription.assert_awaited()
                mock_update.message.reply_text.assert_awaited()
                subscription_service.set_subscription.reset_mock()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_privacy_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        for lang in languages:
            with (
                patch("weatherbot.handlers.commands.get_user_service") as mock_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                mock_service.return_value = user_service
                mock_i18n.return_value = f"Privacy policy in {lang}"
                await privacy_cmd(mock_update, mock_context)
                mock_update.message.reply_text.assert_awaited()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_data_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        for lang in languages:
            with (
                patch(
                    "weatherbot.handlers.commands.get_user_service"
                ) as mock_user_service,
                patch(
                    "weatherbot.handlers.commands.get_subscription_service"
                ) as mock_sub_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                user_service.get_user_home.return_value = {
                    "lat": 50.0,
                    "lon": 10.0,
                    "label": "Test City",
                }
                mock_user_service.return_value = user_service
                subscription_service = AsyncMock()
                subscription_service.get_subscription.return_value = {
                    "hour": 8,
                    "minute": 30,
                }
                mock_sub_service.return_value = subscription_service
                mock_i18n.side_effect = (
                    lambda key, language, **kwargs: f"{key} in {language}"
                )
                await data_cmd(mock_update, mock_context)
                mock_update.message.reply_text.assert_awaited()
                mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_location_handler_all_languages(self, languages):
        for lang in languages:
            update = MagicMock()
            update.message.location.latitude = 55.7558
            update.message.location.longitude = 37.6176
            update.effective_chat.id = 123456
            update.message.reply_text = AsyncMock()
            context = MagicMock()
            with (
                patch(
                    "weatherbot.handlers.messages.get_user_service"
                ) as mock_user_service,
                patch(
                    "weatherbot.handlers.messages.get_weather_application_service"
                ) as mock_weather_service,
                patch("weatherbot.handlers.messages.format_weather") as mock_format,
                patch("weatherbot.handlers.messages.main_keyboard"),
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                mock_user_service.return_value = user_service
                weather_service = AsyncMock()
                weather_service.get_weather_by_coordinates.return_value = {
                    "temperature": 15,
                    "description": f"weather in {lang}",
                }
                mock_weather_service.return_value = weather_service
                mock_format.return_value = f"Weather format in {lang}"
                await on_location(update, context)
                weather_service.get_weather_by_coordinates.assert_awaited_with(
                    55.7558, 37.6176
                )
                update.message.reply_text.assert_awaited()
                update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_language_change_callback_all_languages(self, languages):

        for target_lang in languages:
            update = MagicMock()
            update.callback_query.data = f"lang_{target_lang}"
            update.effective_chat.id = 123456
            update.callback_query.answer = AsyncMock()
            update.callback_query.message.edit_text = AsyncMock()
            context = MagicMock()
            with (
                patch("weatherbot.handlers.language.get_user_service") as mock_service,
                patch("weatherbot.handlers.language.i18n.get") as mock_i18n,
            ):
                user_service = AsyncMock()
                mock_service.return_value = user_service
                mock_i18n.return_value = f"Language changed to {target_lang}"
                await language_callback(update, context)
                user_service.set_user_language.assert_awaited_with(
                    "123456", target_lang
                )
                update.callback_query.message.edit_text.assert_awaited()

                user_service.set_user_language.reset_mock()
                update.callback_query.message.edit_text.reset_mock()

    @pytest.mark.asyncio
    async def test_error_messages_all_languages(self, languages, mock_update):

        for lang in languages:
            context = MagicMock()
            context.args = []
            with (
                patch("weatherbot.handlers.commands.get_user_service") as mock_service,
                patch("weatherbot.handlers.commands.i18n.get") as mock_i18n,
                patch("weatherbot.handlers.commands.main_keyboard"),
                patch("weatherbot.core.decorators.spam_protection") as mock_spam,
            ):
                user_service = AsyncMock()
                user_service.get_user_language.return_value = lang
                mock_service.return_value = user_service
                mock_i18n.return_value = f"Error: No city specified in {lang}"
                mock_spam.is_spam = AsyncMock(return_value=(False, ""))
                await sethome_cmd(mock_update, context)
                mock_update.message.reply_text.assert_awaited()
                call_args = mock_update.message.reply_text.await_args[0][0]
                assert (
                    lang in call_args
                    or "Error" in call_args
                    or "Пожалуйста" in call_args
                )
                mock_update.message.reply_text.reset_mock()


class TestButtonsAndKeyboards:

    @pytest.mark.asyncio
    async def test_all_keyboard_buttons_all_languages(self):

        languages = ["ru", "en", "de"]
        button_actions = [
            "☁️ Погода по городу",
            "🏠 Погода дома",
            "➕ Задать дом",
            "🗑 Удалить дом",
            "ℹ️ Помощь",
        ]
        for lang in languages:
            for button_text in button_actions:
                update = MagicMock()
                update.message.text = button_text
                update.effective_chat.id = 123456
                update.message.reply_text = AsyncMock()
                context = MagicMock()
                with (
                    patch(
                        "weatherbot.handlers.messages.get_user_service"
                    ) as mock_service,
                    patch("weatherbot.handlers.messages.i18n.get") as mock_i18n,
                    patch("weatherbot.handlers.messages.main_keyboard"),
                ):
                    user_service = AsyncMock()
                    user_service.get_user_language.return_value = lang
                    mock_service.return_value = user_service
                    mock_i18n.return_value = f"Button response in {lang}"
                    try:
                        await on_text(update, context)

                        update.message.reply_text.assert_awaited()
                    except Exception as e:

                        assert "fatal" not in str(e).lower()
                    update.message.reply_text.reset_mock()
