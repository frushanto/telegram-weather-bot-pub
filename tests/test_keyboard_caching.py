"""
Tests for keyboard caching behavior after language changes.

When users change their language preference, Telegram clients may continue
to display the old keyboard while the server has updated to the new language.
This causes button text mismatches that must be handled gracefully.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from weatherbot.handlers.messages import (
    MessageHandlerDependencies,
    configure_message_handlers,
    on_text,
)
from weatherbot.presentation.i18n import i18n


@pytest.fixture
def mock_update():
    """Create a mock Telegram update with configurable message text."""
    user = MagicMock(spec=User)
    user.id = 123456
    user.first_name = "Test"
    user.username = "testuser"

    chat = MagicMock(spec=Chat)
    chat.id = 123456
    chat.type = "private"

    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.chat_id = 123456

    update = MagicMock(spec=Update)
    update.effective_chat = chat
    update.message = message
    update.effective_user = user

    return update


@pytest.fixture
def mock_context():
    """Create a mock PTB context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.application = MagicMock()
    context.application.job_queue = AsyncMock()
    return context


@pytest.fixture
def mock_services():
    """Create mock services for dependency injection."""
    user_service = AsyncMock()
    user_service.get_user_language = AsyncMock(return_value="ru")
    user_service.get_user_home = AsyncMock(return_value=None)

    weather_service = AsyncMock()

    state_store = MagicMock()
    state_store.get_state = MagicMock()
    state_store.get_state.return_value = MagicMock(mode="IDLE")
    state_store.is_awaiting = MagicMock(return_value=False)

    subscription_presenter = AsyncMock()

    quota_notifier = AsyncMock()

    schedule_subscription = AsyncMock()

    weather_formatter = MagicMock(return_value="Formatted weather")

    deps = MessageHandlerDependencies(
        user_service=user_service,
        weather_service=weather_service,
        state_store=state_store,
        subscription_presenter=subscription_presenter,
        quota_notifier=quota_notifier,
        schedule_subscription=schedule_subscription,
        weather_formatter=weather_formatter,
    )

    configure_message_handlers(deps)
    return deps


@pytest.mark.asyncio
async def test_help_button_works_with_english_keyboard_and_russian_language(
    mock_update, mock_context, mock_services
):
    """
    Test that Help button works when cached English keyboard is shown but
    user's language is set to Russian.

    Scenario:
    1. User changes language from EN to RU
    2. Telegram client still shows cached English keyboard with "ℹ️ Help"
    3. User presses "ℹ️ Help" button
    4. Bot should recognize it as help button, not treat it as city name
    """
    # User's current language is Russian
    mock_services.user_service.get_user_language.return_value = "ru"

    # But the keyboard button text is English (cached)
    mock_update.message.text = "ℹ️ Help"
    mock_update.message.reply_text = AsyncMock()

    # Execute handler
    await on_text(mock_update, mock_context)

    # Should reply with help message, not try to geocode "Help" as a city
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    help_text = call_args[0][0]

    # Verify it's a help message (contains version info)
    assert "3.1.2" in help_text  # Version should be in help text
    assert "Русский" in help_text or "Russian" in help_text or "ru" in help_text

    # Should NOT have tried to geocode
    mock_services.weather_service.get_weather_by_city.assert_not_called()


@pytest.mark.asyncio
async def test_weather_home_button_works_across_languages(
    mock_update, mock_context, mock_services
):
    """
    Test Weather Home button works with any cached language variant.
    """
    # User language is German
    mock_services.user_service.get_user_language.return_value = "de"

    # But Russian keyboard is cached
    mock_update.message.text = "🌦 Погода дома"
    mock_update.message.reply_text = AsyncMock()

    # No home set, should get "home not set" message
    mock_services.user_service.get_user_home.return_value = None

    await on_text(mock_update, mock_context)

    # Should handle as home weather button (even though text is Russian but user is German)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    response_text = call_args[0][0]

    # Should get German "home not set" message
    german_home_not_set = i18n.get("home_not_set", "de")
    assert response_text == german_home_not_set


@pytest.mark.asyncio
async def test_weather_city_button_works_across_languages(
    mock_update, mock_context, mock_services
):
    """
    Test Weather City button works with any cached language variant.
    """
    # User language is English
    mock_services.user_service.get_user_language.return_value = "en"

    # But German keyboard is cached
    mock_update.message.text = "☁️ Stadtwetter"  # German: City Weather
    mock_update.message.reply_text = AsyncMock()

    await on_text(mock_update, mock_context)

    # Should prompt for city input in English
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    response_text = call_args[0][0]

    english_enter_city = i18n.get("enter_city", "en")
    assert response_text == english_enter_city

    # Should have set conversation state to await city input
    mock_services.state_store.set_awaiting_mode.assert_called_once()


@pytest.mark.asyncio
async def test_all_button_variants_recognized_simultaneously(
    mock_update, mock_context, mock_services
):
    """
    Test that all language variants of each button are recognized.
    """
    mock_services.user_service.get_user_language.return_value = "en"
    mock_update.message.reply_text = AsyncMock()

    # Test all Help button variants
    help_variants = [
        "ℹ️ Help",
        "ℹ️ Помощь",
        "ℹ️ Hilfe",
        "Help",  # Without emoji (emoji normalization)
        "Помощь",
        "Hilfe",
    ]

    for variant in help_variants:
        mock_update.message.text = variant
        mock_update.message.reply_text.reset_mock()

        await on_text(mock_update, mock_context)

        # Each variant should trigger help response
        assert mock_update.message.reply_text.called, f"Failed for variant: {variant}"
        call_args = mock_update.message.reply_text.call_args
        response = call_args[0][0]
        assert "3.1.2" in response, f"Help text missing for variant: {variant}"


@pytest.mark.asyncio
async def test_button_not_geocoded_as_city(mock_update, mock_context, mock_services):
    """
    Regression test: Ensure button text is never geocoded as a city name.

    This was the original bug - when language changed, button text
    like "ℹ️ Help" was treated as a city and geocoded.
    """
    mock_services.user_service.get_user_language.return_value = "ru"

    # Simulate pressing Help button with English text
    mock_update.message.text = "ℹ️ Help"
    mock_update.message.reply_text = AsyncMock()

    await on_text(mock_update, mock_context)

    # Should NOT try to geocode button text
    mock_services.weather_service.geocode_city.assert_not_called()
    mock_services.weather_service.get_weather_by_city.assert_not_called()

    # Should respond with help text
    assert mock_update.message.reply_text.called
