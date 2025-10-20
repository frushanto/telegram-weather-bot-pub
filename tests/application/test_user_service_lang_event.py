"""Tests for UserService language change event publication."""

from unittest.mock import AsyncMock

import pytest

from weatherbot.application.user_service import UserService
from weatherbot.core.events import EventBus, UserLanguageChanged
from weatherbot.domain.repositories import UserRepository


@pytest.mark.asyncio
async def test_set_user_language_publishes_event():
    """Test that set_user_language publishes UserLanguageChanged event."""
    # Setup
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_user_data.return_value = {}
    mock_repo.save_user_data = AsyncMock()

    event_bus = EventBus()
    published_events = []

    async def event_subscriber(event: UserLanguageChanged):
        published_events.append(event)

    event_bus.subscribe(UserLanguageChanged, event_subscriber)

    user_service = UserService(mock_repo, timezone_service=None, event_bus=event_bus)

    # Execute
    await user_service.set_user_language("12345", "en")

    # Verify
    assert len(published_events) == 1
    event = published_events[0]
    assert isinstance(event, UserLanguageChanged)
    assert event.chat_id == 12345
    assert event.lang == "en"


@pytest.mark.asyncio
async def test_set_user_language_without_event_bus():
    """Test that set_user_language works without event bus."""
    # Setup
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_user_data.return_value = {}
    mock_repo.save_user_data = AsyncMock()

    user_service = UserService(mock_repo, timezone_service=None, event_bus=None)

    # Execute - should not raise error
    await user_service.set_user_language("12345", "de")

    # Verify repo was called
    mock_repo.save_user_data.assert_called_once()


@pytest.mark.asyncio
async def test_set_user_language_event_contains_correct_data():
    """Test that published event contains correct chat_id and language."""
    mock_repo = AsyncMock(spec=UserRepository)
    mock_repo.get_user_data.return_value = {}
    mock_repo.save_user_data = AsyncMock()

    event_bus = EventBus()
    captured_event = None

    async def capture_event(event: UserLanguageChanged):
        nonlocal captured_event
        captured_event = event

    event_bus.subscribe(UserLanguageChanged, capture_event)

    user_service = UserService(mock_repo, timezone_service=None, event_bus=event_bus)

    # Test with different chat_id and language
    chat_id = "999888"
    language = "ru"

    await user_service.set_user_language(chat_id, language)

    assert captured_event is not None
    assert captured_event.chat_id == 999888
    assert captured_event.lang == "ru"
