"""Telegram-specific presentation adapters."""

from .command_menu import (
    build_commands,
    set_commands_for_chat,
    set_commands_global,
)

__all__ = [
    "build_commands",
    "set_commands_for_chat",
    "set_commands_global",
]
