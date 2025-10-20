"""Tests for command menu presentation adapter."""

import pytest
from telegram import BotCommand

from weatherbot.presentation.i18n import Localization
from weatherbot.presentation.telegram.command_menu import (
    build_commands,
    clear_command_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear command cache before each test."""
    clear_command_cache()
    yield
    clear_command_cache()


def test_build_commands_english():
    """Test command building for English."""
    i18n = Localization()
    commands = build_commands("en", i18n)

    assert len(commands) == 3
    assert commands[0].command == "start"
    assert (
        "Start" in commands[0].description or "start" in commands[0].description.lower()
    )
    assert commands[1].command == "weather"
    assert "weather" in commands[1].description.lower()
    assert commands[2].command == "help"
    assert "help" in commands[2].description.lower()


def test_build_commands_russian():
    """Test command building for Russian."""
    i18n = Localization()
    commands = build_commands("ru", i18n)

    assert len(commands) == 3
    assert commands[0].command == "start"
    # Just check that description is not empty
    assert commands[0].description
    assert len(commands[0].description) > 0


def test_build_commands_german():
    """Test command building for German."""
    i18n = Localization()
    commands = build_commands("de", i18n)

    assert len(commands) == 3
    assert commands[0].command == "start"
    assert any(
        keyword in commands[0].description.lower() for keyword in ["start", "bot"]
    )


def test_build_commands_fallback_to_english():
    """Test fallback to English for unknown language."""
    i18n = Localization()
    commands = build_commands("unknown", i18n)

    # Should still return commands (falling back to English)
    assert len(commands) == 3
    assert all(isinstance(cmd, BotCommand) for cmd in commands)


def test_build_commands_caching():
    """Test that commands are cached per language."""
    i18n = Localization()

    commands_en_1 = build_commands("en", i18n)
    commands_en_2 = build_commands("en", i18n)

    # Should return the same cached list
    assert commands_en_1 is commands_en_2


@pytest.mark.asyncio
async def test_set_commands_for_chat():
    """Test setting commands for a specific chat."""
    from unittest.mock import AsyncMock

    from weatherbot.presentation.telegram.command_menu import set_commands_for_chat

    mock_bot = AsyncMock()
    i18n = Localization()
    chat_id = 12345

    await set_commands_for_chat(mock_bot, chat_id, "en", i18n)

    # Verify bot.set_my_commands was called with correct scope
    mock_bot.set_my_commands.assert_called_once()
    call_args = mock_bot.set_my_commands.call_args

    commands = call_args.kwargs["commands"]
    scope = call_args.kwargs["scope"]

    assert len(commands) == 3
    assert scope.chat_id == chat_id


@pytest.mark.asyncio
async def test_set_commands_global():
    """Test setting global commands."""
    from unittest.mock import AsyncMock

    from weatherbot.presentation.telegram.command_menu import set_commands_global

    mock_bot = AsyncMock()
    i18n = Localization()

    await set_commands_global(mock_bot, "ru", i18n)

    # Verify bot.set_my_commands was called with default scope and language_code
    mock_bot.set_my_commands.assert_called_once()
    call_args = mock_bot.set_my_commands.call_args

    commands = call_args.kwargs["commands"]
    language_code = call_args.kwargs["language_code"]

    assert len(commands) == 3
    assert language_code == "ru"
