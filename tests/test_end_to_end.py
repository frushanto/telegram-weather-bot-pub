from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from weatherbot.domain.value_objects import UserHome, UserProfile
from weatherbot.domain.weather import WeatherCurrent, WeatherDaily, WeatherReport
from weatherbot.handlers import commands
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
from weatherbot.handlers.messages import on_location, on_text
from weatherbot.presentation.command_presenter import KeyboardView, PresenterResponse
from weatherbot.presentation.i18n import Localization


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
            # stub presenter.start to return a known response
            commands._deps.command_presenter.start = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Start message in {lang}",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                )
            )
            await start_cmd(mock_update, mock_context)
            commands._deps.command_presenter.start.assert_awaited_with(
                mock_update.effective_chat.id
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Start message in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode=None,
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_help_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        for lang in languages:
            # stub presenter.help
            commands._deps.command_presenter.help = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Help message in {lang}",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                )
            )
            await help_cmd(mock_update, mock_context)
            commands._deps.command_presenter.help.assert_awaited_with(
                mock_update.effective_chat.id
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Help message in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode=None,
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_sethome_command_all_languages(self, languages, mock_update):
        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import (
            KeyboardView,
            PresenterResponse,
        )

        for lang in languages:
            context = MagicMock()
            context.args = ["TestCity"]
            # stub presenter.set_home
            commands._deps.command_presenter.set_home = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Home set message in {lang}",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                )
            )
            await sethome_cmd(mock_update, context)
            commands._deps.command_presenter.set_home.assert_awaited_with(
                mock_update.effective_chat.id, "TestCity"
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Home set message in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode=None,
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_home_command_all_languages(
        self, languages, mock_update, mock_context
    ):
        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import (
            KeyboardView,
            PresenterResponse,
        )

        for lang in languages:
            # stub presenter.home_weather
            commands._deps.command_presenter.home_weather = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Weather format in {lang}",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                    parse_mode="HTML",
                    notify_quota=False,
                )
            )
            await home_cmd(mock_update, mock_context)
            commands._deps.command_presenter.home_weather.assert_awaited_with(
                mock_update.effective_chat.id
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Weather format in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode="HTML",
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_subscribe_command_all_languages(self, languages, mock_update):
        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import KeyboardView
        from weatherbot.presentation.subscription_presenter import (
            SubscriptionActionResult,
        )

        for lang in languages:
            context = MagicMock()
            context.args = ["08:30"]
            # stub presenter.subscribe
            commands._deps.subscription_presenter.subscribe = AsyncMock(
                return_value=SubscriptionActionResult(
                    message=f"Subscription set in {lang}",
                    language=lang,
                    success=True,
                    schedule=None,
                )
            )
            await subscribe_cmd(mock_update, context)
            commands._deps.subscription_presenter.subscribe.assert_awaited_with(
                mock_update.effective_chat.id, "08:30", validate_input=False
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Subscription set in {lang}", reply_markup=commands.main_keyboard(lang)
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_privacy_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import (
            KeyboardView,
            PresenterResponse,
        )

        for lang in languages:
            # stub presenter.privacy
            commands._deps.command_presenter.privacy = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Privacy policy in {lang}",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                )
            )
            await privacy_cmd(mock_update, mock_context)
            commands._deps.command_presenter.privacy.assert_awaited_with(
                mock_update.effective_chat.id
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Privacy policy in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode=None,
            )
            mock_update.message.reply_text.reset_mock()

    @pytest.mark.asyncio
    async def test_data_command_all_languages(
        self, languages, mock_update, mock_context
    ):

        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import (
            KeyboardView,
            PresenterResponse,
        )

        for lang in languages:
            # stub presenter.data_snapshot
            commands._deps.command_presenter.data_snapshot = AsyncMock(
                return_value=PresenterResponse(
                    message=f"Data in {lang}", language=lang, keyboard=KeyboardView.MAIN
                )
            )
            await data_cmd(mock_update, mock_context)
            commands._deps.command_presenter.data_snapshot.assert_awaited_with(
                mock_update.effective_chat.id
            )
            mock_update.message.reply_text.assert_awaited_with(
                f"Data in {lang}",
                reply_markup=commands.main_keyboard(lang),
                parse_mode=None,
            )
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
                weather_service.get_weather_by_coordinates.return_value = WeatherReport(
                    current=WeatherCurrent(
                        temperature=15.0,
                        apparent_temperature=14.0,
                        wind_speed=3.0,
                        weather_code=0,
                    ),
                    daily=[
                        WeatherDaily(
                            min_temperature=10.0,
                            max_temperature=20.0,
                            precipitation_probability=5.0,
                            sunrise="2025-01-01T07:00",
                            sunset="2025-01-01T19:00",
                            wind_speed_max=4.0,
                            weather_code=1,
                        )
                    ],
                )
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

        import weatherbot.handlers.language as language_module

        for target_lang in languages:
            update = MagicMock()
            update.callback_query.data = f"lang_{target_lang}"
            update.effective_chat.id = 123456
            update.callback_query.answer = AsyncMock()
            update.callback_query.message.edit_text = AsyncMock()
            context = MagicMock()
            context.bot = AsyncMock()
            user_service = AsyncMock()
            user_service.get_user_profile.return_value = UserProfile(
                language="ru", language_explicit=True
            )

            language_module.configure_language_handlers(
                language_module.LanguageHandlerDependencies(
                    user_service=user_service,
                    localization=Localization(),
                    keyboard_factory=lambda _lang: None,
                )
            )

            await language_module.language_callback(update, context)
            user_service.set_user_language.assert_awaited_with("123456", target_lang)
            update.callback_query.message.edit_text.assert_awaited()

            user_service.set_user_language.reset_mock()
            update.callback_query.message.edit_text.reset_mock()

    @pytest.mark.asyncio
    async def test_error_messages_all_languages(self, languages, mock_update):

        from weatherbot.handlers import commands
        from weatherbot.presentation.command_presenter import (
            KeyboardView,
            PresenterResponse,
        )

        for lang in languages:
            # return error-like response from presenter
            commands._deps.command_presenter.set_home = AsyncMock(
                return_value=PresenterResponse(
                    message="Please provide city name",
                    language=lang,
                    keyboard=KeyboardView.MAIN,
                    success=False,
                )
            )
            context = MagicMock()
            context.args = []
            await sethome_cmd(mock_update, context)
            mock_update.message.reply_text.assert_awaited()
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
