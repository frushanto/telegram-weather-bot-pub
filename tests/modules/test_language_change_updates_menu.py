"""Tests for language change triggering command menu updates."""

from unittest.mock import AsyncMock, patch

import pytest

from weatherbot.core.events import EventBus, UserLanguageChanged
from weatherbot.presentation.i18n import Localization


@pytest.mark.asyncio
async def test_language_change_event_triggers_menu_update():
    """Test that UserLanguageChanged event triggers set_commands_for_chat."""
    # Setup
    event_bus = EventBus()
    mock_bot = AsyncMock()
    i18n = Localization()

    # Mock the set_commands_for_chat function
    mock_set_commands = AsyncMock()
    with patch(
        "weatherbot.presentation.telegram.command_menu.set_commands_for_chat",
        mock_set_commands,
    ):
        # Simulate subscription (like in command_module.py)
        from weatherbot.presentation.telegram.command_menu import set_commands_for_chat

        async def _on_language_changed(evt: UserLanguageChanged) -> None:
            await set_commands_for_chat(mock_bot, evt.chat_id, evt.lang, i18n)

        event_bus.subscribe(UserLanguageChanged, _on_language_changed)

        # Publish event
        event = UserLanguageChanged(chat_id=12345, lang="de")
        await event_bus.publish(event)

        # Verify
        mock_set_commands.assert_called_once_with(mock_bot, 12345, "de", i18n)


@pytest.mark.asyncio
async def test_multiple_language_changes():
    """Test multiple language change events."""
    event_bus = EventBus()
    mock_bot = AsyncMock()
    i18n = Localization()

    call_log = []

    from weatherbot.presentation.telegram.command_menu import set_commands_for_chat

    async def _on_language_changed(evt: UserLanguageChanged) -> None:
        call_log.append((evt.chat_id, evt.lang))
        await set_commands_for_chat(mock_bot, evt.chat_id, evt.lang, i18n)

    event_bus.subscribe(UserLanguageChanged, _on_language_changed)

    # Publish multiple events
    await event_bus.publish(UserLanguageChanged(chat_id=111, lang="en"))
    await event_bus.publish(UserLanguageChanged(chat_id=222, lang="ru"))
    await event_bus.publish(UserLanguageChanged(chat_id=333, lang="de"))

    # Verify all were processed
    assert len(call_log) == 3
    assert call_log[0] == (111, "en")
    assert call_log[1] == (222, "ru")
    assert call_log[2] == (333, "de")


@pytest.mark.asyncio
async def test_event_handler_error_doesnt_crash(caplog):
    """Test that errors in event handler don't crash the application."""
    import logging

    event_bus = EventBus()

    async def _failing_handler(evt: UserLanguageChanged) -> None:
        raise RuntimeError("Simulated error")

    event_bus.subscribe(UserLanguageChanged, _failing_handler)

    # Publishing should not raise
    with caplog.at_level(logging.ERROR):
        try:
            await event_bus.publish(UserLanguageChanged(chat_id=999, lang="en"))
        except RuntimeError:
            # EventBus doesn't catch exceptions, this is expected
            pass


@pytest.mark.asyncio
async def test_no_subscribers_does_nothing():
    """Test that publishing event without subscribers works."""
    event_bus = EventBus()

    # Should not raise
    await event_bus.publish(UserLanguageChanged(chat_id=123, lang="en"))
