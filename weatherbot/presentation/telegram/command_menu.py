"""Telegram command menu management for multilingual per-chat command lists."""

from __future__ import annotations

import logging
from typing import Dict, List

from telegram import Bot, BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from ..i18n import Localization

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid loading locales on every call
_command_cache: Dict[str, List[BotCommand]] = {}


def build_commands(lang: str, i18n: Localization) -> List[BotCommand]:
    """
    Build a list of BotCommand objects for the given language.

    Falls back to 'en' if the key is not found in the specified language.

    Args:
        lang: Language code (e.g., 'en', 'de', 'ru')
        i18n: Localization instance

    Returns:
        List of BotCommand objects
    """
    # Check cache first
    if lang in _command_cache:
        return _command_cache[lang]

    # Define the command keys we want to expose
    command_keys = ["start", "weather", "help"]
    commands = []

    for key in command_keys:
        # Get command description using flat keys: cmd_start_desc, cmd_weather_desc, etc.
        cmd_desc = i18n.get(f"cmd_{key}_desc", lang=lang, default="")

        # Fallback to English if description is empty
        if not cmd_desc:
            cmd_desc = i18n.get(f"cmd_{key}_desc", lang="en", default=key)

        commands.append(BotCommand(command=key, description=cmd_desc))

    # Cache the result
    _command_cache[lang] = commands
    logger.debug(f"Built {len(commands)} commands for language '{lang}'")

    return commands


async def set_commands_for_chat(
    bot: Bot, chat_id: int, lang: str, i18n: Localization
) -> None:
    """
    Set bot commands for a specific chat with per-chat scope.

    Args:
        bot: Telegram Bot instance
        chat_id: Chat ID to set commands for
        lang: Language code
        i18n: Localization instance
    """
    try:
        commands = build_commands(lang, i18n)
        scope = BotCommandScopeChat(chat_id=chat_id)
        await bot.set_my_commands(commands=commands, scope=scope)
        logger.info(
            f"Set {len(commands)} commands for chat {chat_id} in language '{lang}'"
        )
    except Exception as e:
        logger.exception(
            f"Failed to set commands for chat {chat_id} in language '{lang}': {e}"
        )


async def set_commands_global(bot: Bot, lang: str, i18n: Localization) -> None:
    """
    Set global bot commands with a language_code scope.

    This seeds default commands for users with a specific language
    without overriding per-chat scopes.

    Args:
        bot: Telegram Bot instance
        lang: Language code
        i18n: Localization instance
    """
    try:
        commands = build_commands(lang, i18n)
        scope = BotCommandScopeDefault()
        await bot.set_my_commands(commands=commands, scope=scope, language_code=lang)
        logger.info(f"Set global commands for language '{lang}'")
    except Exception as e:
        logger.exception(f"Failed to set global commands for language '{lang}': {e}")


def clear_command_cache() -> None:
    """Clear the in-memory command cache. Useful for tests or locale reloads."""
    global _command_cache
    _command_cache = {}
    logger.debug("Command cache cleared")
